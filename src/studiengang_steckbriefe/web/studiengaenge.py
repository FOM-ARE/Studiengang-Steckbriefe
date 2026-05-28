"""Studiengaenge-Blueprint: Listet verfuegbare Studiengaenge."""

import traceback

from flask import Blueprint, jsonify

from studiengang_steckbriefe.services import steckbrief as svc
from studiengang_steckbriefe.web.auth import login_required

studiengaenge_bp = Blueprint("studiengaenge", __name__)


@studiengaenge_bp.route("/api/studiengaenge")
@login_required
def studiengaenge():
    """Gibt die Liste aller aktiven Studiengaenge zurueck."""
    try:
        data = svc.get_studiengaenge()
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
