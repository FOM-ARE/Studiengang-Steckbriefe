"""Cache-Management-Blueprint: Admin-Endpoints fuer Cache-Steuerung."""

import traceback

from flask import Blueprint, jsonify

from studiengang_steckbriefe.services.cache import (
    cache_clear,
    cache_delete,
    cache_status,
)
from studiengang_steckbriefe.services.config_db import reload_config
from studiengang_steckbriefe.web.auth import admin_required

cache_mgmt_bp = Blueprint("cache_mgmt", __name__)


@cache_mgmt_bp.route("/api/cache/status")
@admin_required
def status():
    """Gibt den Cache-Status zurueck."""
    return jsonify(success=True, data=cache_status())


@cache_mgmt_bp.route("/api/cache/clear", methods=["POST"])
@admin_required
def clear():
    """Leert den gesamten Cache."""
    cache_clear()
    return jsonify(success=True, message="Cache geleert")


@cache_mgmt_bp.route("/api/cache/clear/<produktkuerzel>/<endpoint>", methods=["POST"])
@admin_required
def clear_entry(produktkuerzel: str, endpoint: str):
    """Loescht einen einzelnen Cache-Eintrag."""
    cache_key = f"{endpoint}_{produktkuerzel}"
    cache_delete(cache_key)
    return jsonify(success=True, message=f"Cache-Eintrag '{cache_key}' geloescht")


@cache_mgmt_bp.route("/api/cache/preload", methods=["POST"])
@admin_required
def preload():
    """Waermt den Cache fuer alle aktiven Studiengaenge vor."""
    from studiengang_steckbriefe.services import steckbrief as svc

    _ENDPOINTS = [
        svc.get_trends,
        svc.get_stammdaten,
        svc.get_studienerfolg,
        svc.get_uebergang,
        svc.get_herkunft,
        svc.get_zuzahler,
        svc.get_vertiefungsrichtungen,
        svc.get_rahmendaten,
        svc.get_aktive_hszen,
        svc.get_anrechnungen,
    ]

    try:
        hsbs = svc.get_studiengaenge()
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

    all_pks: set[str] = set()
    for hsb in hsbs:
        for sg in hsb.get("programmes", []):
            pk = sg.get("produktkuerzel")
            if pk:
                all_pks.add(pk)

    errors: list[str] = []
    endpoints_loaded = 0
    for pk in sorted(all_pks):
        for fn in _ENDPOINTS:
            try:
                fn(pk)
                endpoints_loaded += 1
            except Exception as e:
                errors.append(f"{fn.__name__}({pk}): {e}")

    return jsonify(
        success=True,
        studiengaenge=len(all_pks),
        endpoints_loaded=endpoints_loaded,
        errors=errors,
    )


@cache_mgmt_bp.route("/api/config/reload", methods=["POST"])
@admin_required
def reload_config_endpoint():
    """Laedt die Konfiguration aus MariaDB neu und leert den Cache."""
    reload_config()
    cache_clear()
    return jsonify(success=True, message="Konfiguration neu geladen, Cache geleert")
