"""Steckbrief-Blueprint: Alle Steckbrief-Endpoints (Trends, Stammdaten, etc.).

Delegiert die Fachlogik an services/steckbrief.py.
"""

import traceback

from flask import Blueprint, jsonify

from studiengang_steckbriefe.services import steckbrief as svc
from studiengang_steckbriefe.web.auth import login_required

steckbrief_bp = Blueprint("steckbrief", __name__)


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/trends")
@login_required
def trends(produktkuerzel: str):
    """Zeitreihen und Trends fuer einen Studiengang."""
    try:
        data = svc.get_trends(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/stammdaten")
@login_required
def stammdaten(produktkuerzel: str):
    """Stammdaten (Alter, Geschlecht, Internationalitaet) fuer einen Studiengang."""
    try:
        data = svc.get_stammdaten(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/studienerfolg")
@login_required
def studienerfolg(produktkuerzel: str):
    """Studienerfolg-Kennzahlen fuer einen Studiengang."""
    try:
        data = svc.get_studienerfolg(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/anrechnungen")
@login_required
def anrechnungen(produktkuerzel: str):
    """Anrechnungsstatistiken fuer einen Studiengang."""
    try:
        data = svc.get_anrechnungen(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        tb = traceback.format_exc()
        return jsonify(success=False, error=str(e), traceback=tb), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/uebergang")
@login_required
def uebergang(produktkuerzel: str):
    """Uebergangsquoten (Bachelor -> Master) fuer einen Studiengang."""
    try:
        data = svc.get_uebergang(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/herkunft")
@login_required
def herkunft(produktkuerzel: str):
    """Herkunft der Master-Studierenden."""
    try:
        data = svc.get_herkunft(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        tb = traceback.format_exc()
        return jsonify(success=False, error=str(e), traceback=tb), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/zuzahler")
@login_required
def zuzahler(produktkuerzel: str):
    """Zuzahler-Statistiken fuer einen Studiengang."""
    try:
        data = svc.get_zuzahler(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/vertiefungsrichtungen")
@login_required
def vertiefungsrichtungen(produktkuerzel: str):
    """Vertiefungsrichtungen fuer einen Studiengang."""
    try:
        data = svc.get_vertiefungsrichtungen(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/rahmendaten")
@login_required
def rahmendaten(produktkuerzel: str):
    """Rahmendaten (UE-Verteilung) fuer einen Studiengang."""
    try:
        data = svc.get_rahmendaten(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@steckbrief_bp.route("/api/steckbrief/<produktkuerzel>/hszen")
@login_required
def aktive_hszen(produktkuerzel: str):
    """Aktive Hochschulzentren fuer einen Studiengang."""
    try:
        data = svc.get_aktive_hszen(produktkuerzel)
        return jsonify(success=True, data=data)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
