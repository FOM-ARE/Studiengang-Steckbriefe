"""Debug-Blueprint: Diagnose-Endpoints (nur fuer eingeloggte User)."""

from flask import Blueprint, current_app, jsonify

from studiengang_steckbriefe.services import config_db
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


@debug_bp.route("/api/debug/config")
@login_required
def debug_config():
    """Zeigt den aktuellen Zustand der geladenen Konfiguration."""
    return jsonify(
        success=True,
        db_init_error=current_app.config.get("DB_INIT_ERROR"),
        hsb_config_count=len(config_db.HSB_CONFIG),
        hsb_config_keys=sorted(config_db.HSB_CONFIG.keys()),
        hsb_exclude_kuerzel=config_db.HSB_EXCLUDE_KUERZEL,
        excluded_hsz_count=len(config_db.EXCLUDED_HSZ),
        pk_mapping_count=len(config_db.PK_MAPPING),
        offene_hochschule_gruende_count=len(config_db.OFFENE_HOCHSCHULE_GRUENDE),
    )


@debug_bp.route("/api/debug/token-claims")
@login_required
def debug_token_claims():
    """Zeigt die Entra ID Token-Claims des aktuellen Users (fuer Groups-Test)."""
    from flask import session

    claims = session.get("_debug_claims", {})
    has_groups = "groups" in claims
    return jsonify(
        success=True,
        has_groups_claim=has_groups,
        groups=claims.get("groups", []),
        all_claim_keys=sorted(claims.keys()),
        claims=claims,
    )
