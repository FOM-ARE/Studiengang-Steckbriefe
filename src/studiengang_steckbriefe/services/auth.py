"""Entra ID (MSAL) Authentifizierung und Berechtigungspruefung."""

import logging

import msal
import pyodbc
from flask import current_app, session

logger = logging.getLogger(__name__)

# Rollen-Hierarchie fuer Gruppenauswertung
ROLE_HIERARCHY = {"admin": 3, "write": 2, "read": 1}


class EntraIdAuth:
    """MSAL Confidential Client fuer Entra ID Auth Code Flow."""

    def __init__(self, app):
        self._client_id = app.config["ENTRA_CLIENT_ID"]
        self._client_secret = app.config["ENTRA_CLIENT_SECRET"]
        self._authority = app.config["ENTRA_AUTHORITY"]
        self._redirect_uri = app.config["ENTRA_REDIRECT_URI"]
        self._scope = ["User.Read"]
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


def get_role_from_token_claims(claims: dict, group_mapping: dict[str, str]) -> str | None:
    """Bestimmt die Rolle aus dem groups-Claim im ID-Token.

    Die Gruppen-Object-IDs werden direkt im signierten ID-Token von Microsoft
    mitgeliefert (Token-Konfiguration in der App Registration). Kein
    zusaetzlicher Graph-API-Call und kein Admin Consent noetig.

    Args:
        claims: Die id_token_claims aus dem MSAL-Token.
        group_mapping: Dict {group_object_id: role_name}.

    Returns:
        Die hoechste Rolle oder None.
    """
    user_groups = set(claims.get("groups", []))
    if not user_groups:
        logger.info(
            "Keine Gruppen im Token-Claim gefunden (groups-Claim leer oder nicht konfiguriert)"
        )
        return None

    max_level = 0
    max_role = None
    for group_id, role in group_mapping.items():
        if group_id and group_id in user_groups:
            level = ROLE_HIERARCHY.get(role, 0)
            if level > max_level:
                max_level = level
                max_role = role
    return max_role


# ═══════════════════════════════════════
# Berechtigungspruefung (DB-basiert, Fallback)
# ═══════════════════════════════════════


def _get_perm_connection():
    """Erstellt eine pyodbc-Verbindung zur Berechtigungs-DB (BCW_STA)."""
    host = current_app.config["PERM_DWH_HOST"]
    port = current_app.config["PERM_DWH_PORT"]
    database = current_app.config["PERM_DWH_DATABASE"]
    auth = current_app.config.get("PERM_DWH_AUTHENTICATION", "SQL")

    available = [d for d in pyodbc.drivers() if "SQL Server" in d]
    driver = "{" + available[-1] + "}" if available else "{ODBC Driver 17 for SQL Server}"

    if auth == "Windows":
        conn_str = (
            f"DRIVER={driver};SERVER={host},{port};DATABASE={database};"
            f"Trusted_Connection=yes;TrustServerCertificate=yes;"
        )
    else:
        user = current_app.config.get("PERM_DWH_USER", "")
        password = current_app.config.get("PERM_DWH_PASSWORD", "")
        conn_str = (
            f"DRIVER={driver};SERVER={host},{port};DATABASE={database};"
            f"UID={user};PWD={password};TrustServerCertificate=yes;"
        )
    return pyodbc.connect(conn_str, timeout=10)


def load_app_permissions() -> dict[str, list[dict]]:
    """Laedt Berechtigungen fuer diese App aus BCW_STA.readwrite.App_Berechtigungen.

    Returns:
        Dict: {recht: [{'berechtigt': ..., 'typ': ...}, ...]}
    """
    app_name = current_app.config["APP_NAME"]
    conn = _get_perm_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Berechtigt, Recht, Typ FROM readwrite.App_Berechtigungen"
            " WHERE App = ? AND Aktiv = 1",
            (app_name,),
        )
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    finally:
        conn.close()

    permissions: dict[str, list[dict]] = {}
    for r in rows:
        permissions.setdefault(r["Recht"], []).append(
            {
                "berechtigt": r["Berechtigt"],
                "typ": r["Typ"],
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
