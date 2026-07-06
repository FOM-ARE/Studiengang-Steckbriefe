"""Auth-Blueprint: Entra ID Login/Callback/Logout/Me."""

import secrets
from functools import wraps

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

from studiengang_steckbriefe.services.auth import (
    EntraIdAuth,
    get_user_role,
)

auth_bp = Blueprint("auth", __name__)

LOGIN_PAGE = "main.login_page"


def login_required(f):
    """Decorator: Prueft ob ein User eingeloggt ist."""

    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user:
            return jsonify({"error": "Nicht authentifiziert"}), 401
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator: Prueft ob der User Admin-Rechte hat."""

    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user:
            return jsonify({"error": "Nicht authentifiziert"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "Keine Administratorrechte"}), 403
        return f(*args, **kwargs)

    return decorated


@auth_bp.route("/api/auth/login")
def login():
    """Leitet den User zur Microsoft-Anmeldeseite weiter."""
    try:
        auth = EntraIdAuth(current_app)
        state = secrets.token_urlsafe(32)
        session["auth_state"] = state
        auth_url = auth.get_auth_url(state=state)
        return redirect(auth_url)
    except Exception as exc:
        current_app.logger.exception("Entra ID Login fehlgeschlagen: %s", exc)
        return redirect(url_for(LOGIN_PAGE, error="auth_failed"))


@auth_bp.route("/auth/callback")
def callback():
    """Verarbeitet den Callback von Microsoft nach erfolgreicher Anmeldung."""
    # State validieren (CSRF-Schutz)
    state = request.args.get("state", "")
    if state != session.pop("auth_state", None):
        return redirect(url_for(LOGIN_PAGE, error="invalid_state"))

    auth_code = request.args.get("code")
    if not auth_code:
        return redirect(url_for(LOGIN_PAGE, error="auth_failed"))

    try:
        auth = EntraIdAuth(current_app)
        result = auth.acquire_token(auth_code)

        # User-Info aus Token-Claims extrahieren
        claims = result.get("id_token_claims", {})
        username = claims.get("preferred_username", "").split("@")[0]
        display_name = claims.get("name", username)

        # Berechtigung pruefen
        role = get_user_role(username)
        if not role:
            return redirect(url_for(LOGIN_PAGE, error="no_permission"))

        # Session setzen
        session.permanent = True
        session["user"] = {
            "username": username,
            "displayName": display_name,
            "email": claims.get("preferred_username", ""),
            "role": role,
        }

        return redirect(url_for("main.index"))

    except ValueError:
        return redirect(url_for(LOGIN_PAGE, error="auth_failed"))
    except Exception as exc:
        current_app.logger.exception("Entra ID Callback fehlgeschlagen: %s", exc)
        return redirect(url_for(LOGIN_PAGE, error="auth_failed"))


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """Beendet die Session."""
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/api/auth/me")
def me():
    """Gibt den aktuellen Benutzer zurueck."""
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user})
