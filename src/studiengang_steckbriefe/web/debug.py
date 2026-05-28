"""Debug-Blueprint: Diagnose-Endpoints (nur fuer eingeloggte User)."""

from flask import Blueprint, jsonify

from studiengang_steckbriefe.services.db_connector import query_db
from studiengang_steckbriefe.web.auth import login_required

debug_bp = Blueprint("debug", __name__)


@debug_bp.route("/api/debug/semester-format")
@login_required
def debug_semester():
    """Zeigt die letzten 20 Semesterkuerzel aus dem DWH."""
    try:
        rows = query_db("""
            SELECT DISTINCT TOP 20 Semesterkuerzel
            FROM BCW_DWH.dwh.C_Studierendenzahlen
            ORDER BY Semesterkuerzel DESC
        """)
        return jsonify(success=True, data=rows)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@debug_bp.route("/api/debug/produktkuerzel")
@login_required
def debug_produktkuerzel():
    """Zeigt die verfuegbaren Produktkuerzel."""
    try:
        rows = query_db("""
            SELECT DISTINCT TOP 50 Produktkuerzel, Studiengang, Hochschulbereich
            FROM BCW_DWH.dwh.C_Studierendenzahlen
            WHERE Institut = 'FOM'
            ORDER BY Produktkuerzel
        """)
        return jsonify(success=True, data=rows)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
