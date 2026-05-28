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
    try:
        conn = get_connection()
        release_connection(conn)
        return jsonify(status="ok", database="connected"), 200
    except Exception as e:
        return jsonify(status="error", database="disconnected", error=str(e)), 503
