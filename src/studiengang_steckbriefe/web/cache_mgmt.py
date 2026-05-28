"""Cache-Management-Blueprint: Admin-Endpoints fuer Cache-Steuerung."""

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


@cache_mgmt_bp.route("/api/config/reload", methods=["POST"])
@admin_required
def reload_config_endpoint():
    """Laedt die Konfiguration aus MariaDB neu und leert den Cache."""
    reload_config()
    cache_clear()
    return jsonify(success=True, message="Konfiguration neu geladen, Cache geleert")
