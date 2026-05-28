"""Health-Blueprint: Liefert den Gesundheitsstatus der Anwendung."""

from flask import Blueprint, jsonify

from studiengang_steckbriefe.services.db_connector import (
    get_connection,
    release_connection,
)

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
def health():
    """Prueft die Datenbankverbindung und gibt den Status zurueck."""
    from flask import current_app

    db_init_error = current_app.config.get("DB_INIT_ERROR")
    if db_init_error:
        return jsonify(status="error", stage="startup", error=db_init_error), 503

    try:
        conn = get_connection()
        release_connection(conn)
        return jsonify(status="ok", database="connected"), 200
    except Exception as e:
        return jsonify(status="error", database="disconnected", error=str(e)), 503
