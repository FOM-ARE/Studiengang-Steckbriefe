"""Entra ID (MSAL) Authentifizierung und Berechtigungspruefung."""

import logging

import msal
import requests
from flask import current_app, session

from studiengang_steckbriefe.services import mariadb_connector

logger = logging.getLogger(__name__)

# Mapping: AD-Gruppenname → App-Rolle
GROUP_ROLE_MAPPING = {
    "StudiengangSteckbriefeAdmin": "admin",
    "StudiengangSteckbriefeWrite": "write",
    "StudiengangSteckbriefeRead": "read",
}


class EntraIdAuth:
    """MSAL Confidential Client fuer Entra ID Auth Code Flow."""

    def __init__(self, app):
        self._client_id = app.config["ENTRA_CLIENT_ID"]
        self._client_secret = app.config["ENTRA_CLIENT_SECRET"]
        self._authority = app.config["ENTRA_AUTHORITY"]
        self._redirect_uri = app.config["ENTRA_REDIRECT_URI"]
        self._scope = ["User.Read", "GroupMember.Read.All"]
        self._msal_app = msal.ConfidentialClientApplication(
            self._client_id,
            authority=self._authority,
            client_credential=self._client_secret,
        )

    def get_auth_url(self, state: str | None = None) -> str:
        """Generiert die Authorization-URL fuer den Login-Redirect."""
        return self._msal_app.get_authorization_request_url(
            self._scope,
            redirect_uri=self._redirect_uri,
            state=state,
        )

    def acquire_token(self, auth_code: str) -> dict:
        """Tauscht den Authorization Code gegen Token-Claims.

        Returns:
            Dict mit id_token_claims (Name, E-Mail, OID etc.)
        """
        result = self._msal_app.acquire_token_by_authorization_code(
            auth_code,
            scopes=self._scope,
            redirect_uri=self._redirect_uri,
        )
        if "error" in result:
            raise ValueError(result.get("error_description", "Authentifizierung fehlgeschlagen"))
        return result


# ═══════════════════════════════════════
# Berechtigungspruefung (Gruppen-basiert via Graph API)
# ═══════════════════════════════════════


def get_role_from_groups(access_token: str) -> str | None:
    """Fragt die Gruppenzugehoerigkeit via Microsoft Graph API ab.

    Args:
        access_token: Das Access Token aus dem Auth Code Flow.

    Returns:
        Die hoechste Rolle basierend auf AD-Gruppen oder None.
    """
    role_hierarchy = {"admin": 3, "write": 2, "read": 1}
    try:
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/memberOf?$select=displayName&$top=200",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(
                "Graph API /me/memberOf fehlgeschlagen: %s %s",
                resp.status_code,
                resp.text[:200],
            )
            return None

        groups = resp.json().get("value", [])
        max_level = 0
        max_role = None
        for group in groups:
            name = group.get("displayName", "")
            role = GROUP_ROLE_MAPPING.get(name)
            if role:
                level = role_hierarchy.get(role, 0)
                if level > max_level:
                    max_level = level
                    max_role = role
        return max_role
    except Exception as exc:
        logger.warning("Graph API Gruppenabfrage fehlgeschlagen: %s", exc)
        return None


# ═══════════════════════════════════════
# Berechtigungspruefung (DB-basiert, Fallback)
# ═══════════════════════════════════════


def load_app_permissions() -> dict[str, list[dict]]:
    """Laedt Berechtigungen fuer diese App aus der MariaDB.

    Returns:
        Dict: {recht: [{'berechtigt': ..., 'typ': ..., 'display_name': ...}, ...]}
    """
    app_name = current_app.config["APP_NAME"]
    rows = mariadb_connector.query(
        "SELECT Berechtigt, Recht, Typ FROM t_app_berechtigungen WHERE App = %s AND Aktiv = 1",
        (app_name,),
    )
    permissions: dict[str, list[dict]] = {}
    for r in rows:
        permissions.setdefault(r["Recht"], []).append(
            {
                "berechtigt": r["Berechtigt"],
                "typ": r["Typ"],
                "display_name": "",
            }
        )
    return permissions


def check_permission(username: str, required_role: str = "read") -> bool:
    """Prueft ob ein Benutzer die erforderliche Rolle hat.

    Rollen-Hierarchie: admin > write > read
    """
    role_hierarchy = {"admin": 3, "write": 2, "read": 1}
    required_level = role_hierarchy.get(required_role, 1)

    permissions = load_app_permissions()
    for role, entries in permissions.items():
        role_level = role_hierarchy.get(role, 0)
        if role_level >= required_level:
            for entry in entries:
                if entry["typ"] == "user" and entry["berechtigt"].lower() == username.lower():
                    return True
                # Gruppen-Pruefung koennte hier erweitert werden
    return False


def get_user_role(username: str) -> str | None:
    """Gibt die hoechste Rolle eines Benutzers zurueck oder None."""
    role_hierarchy = {"admin": 3, "write": 2, "read": 1}
    permissions = load_app_permissions()
    max_level = 0
    max_role = None

    for role, entries in permissions.items():
        for entry in entries:
            if entry["typ"] == "user" and entry["berechtigt"].lower() == username.lower():
                level = role_hierarchy.get(role, 0)
                if level > max_level:
                    max_level = level
                    max_role = role
    return max_role


def get_current_user() -> dict | None:
    """Gibt den aktuellen User aus der Session zurueck oder None."""
    return session.get("user")


def is_authenticated() -> bool:
    """Prueft ob ein User eingeloggt ist."""
    return "user" in session
