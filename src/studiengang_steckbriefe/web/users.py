"""Users-Blueprint: Admin-Panel fuer Benutzerverwaltung."""

from flask import Blueprint, jsonify, request

from studiengang_steckbriefe.services import mariadb_connector
from studiengang_steckbriefe.web.auth import admin_required

users_bp = Blueprint("users", __name__)


@users_bp.route("/api/users", methods=["GET"])
@admin_required
def get_users():
    """Gibt alle Berechtigungseintraege fuer diese App zurueck."""
    from flask import current_app

    app_name = current_app.config["APP_NAME"]
    rows = mariadb_connector.query(
        "SELECT Id, Berechtigt, Recht, Typ, DisplayName, Aktiv "
        "FROM t_app_berechtigungen WHERE App = %s ORDER BY Recht, Berechtigt",
        (app_name,),
    )
    return jsonify({"users": rows})


@users_bp.route("/api/users", methods=["POST"])
@admin_required
def add_user():
    """Fuegt einen neuen Berechtigungseintrag hinzu."""
    from flask import current_app

    data = request.get_json(silent=True) or {}
    berechtigt = data.get("username", "").strip()
    typ = data.get("typ", "user").strip()

    if not berechtigt:
        return jsonify({"error": "Name erforderlich"}), 400
    if typ not in ("user", "gruppe"):
        return jsonify({"error": "Typ muss 'user' oder 'gruppe' sein"}), 400

    app_name = current_app.config["APP_NAME"]

    # Pruefen ob Eintrag bereits existiert
    existing = mariadb_connector.query(
        "SELECT Id FROM t_app_berechtigungen WHERE App = %s AND Berechtigt = %s",
        (app_name, berechtigt),
    )
    if existing:
        return jsonify({"error": "Eintrag existiert bereits"}), 409

    mariadb_connector.execute(
        "INSERT INTO t_app_berechtigungen (App, Berechtigt, Recht, Typ, Aktiv) "
        "VALUES (%s, %s, %s, %s, %s)",
        (app_name, berechtigt, "read", typ, 1),
    )
    result = {
        "ok": True,
        "user": {"berechtigt": berechtigt, "recht": "read", "typ": typ},
    }
    return jsonify(result), 201


@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id: int):
    """Aendert das Recht eines Berechtigungseintrags."""
    data = request.get_json(silent=True) or {}
    recht = data.get("recht", "").strip()

    if recht not in ("read", "write", "admin"):
        return jsonify({"error": "Recht muss 'read', 'write' oder 'admin' sein"}), 400

    affected = mariadb_connector.execute(
        "UPDATE t_app_berechtigungen SET Recht = %s WHERE Id = %s",
        (recht, user_id),
    )
    if affected == 0:
        return jsonify({"error": "Eintrag nicht gefunden"}), 404
    return jsonify({"ok": True})


@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id: int):
    """Deaktiviert einen Berechtigungseintrag."""
    from flask import session

    # Admin kann sich nicht selbst entfernen
    current_user = session.get("user", {}).get("username", "")
    existing = mariadb_connector.query(
        "SELECT Berechtigt FROM t_app_berechtigungen WHERE Id = %s", (user_id,)
    )
    if existing and existing[0]["Berechtigt"].lower() == current_user.lower():
        return jsonify({"error": "Admin kann sich nicht selbst entfernen"}), 400

    affected = mariadb_connector.execute(
        "UPDATE t_app_berechtigungen SET Aktiv = 0 WHERE Id = %s", (user_id,)
    )
    if affected == 0:
        return jsonify({"error": "Eintrag nicht gefunden"}), 404
    return jsonify({"ok": True})
