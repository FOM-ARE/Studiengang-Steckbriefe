"""Cache-Management-Blueprint: Admin-Endpoints fuer Cache-Steuerung."""

import traceback

from flask import Blueprint, jsonify

from studiengang_steckbriefe.services.cache import (
    cache_clear,
    cache_delete,
    cache_status,
)
from studiengang_steckbriefe.services.config_db import reload_config
from studiengang_steckbriefe.web.auth import admin_required, login_required

cache_mgmt_bp = Blueprint("cache_mgmt", __name__)


@cache_mgmt_bp.route("/api/cache/datenstand")
@login_required
def datenstand():
    """Gibt den Datenstand (letzter Cache-Aufbau) zurueck – fuer alle User."""
    import datetime

    info = cache_status()
    newest = info.get("newest")
    if newest:
        dt = datetime.datetime.fromtimestamp(newest)
        text = dt.strftime("%d.%m.%Y %H:%M")
    else:
        text = None
    return jsonify(success=True, datenstand=text)


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


_preload_status: dict = {"running": False, "done": 0, "total": 0, "errors": []}


def _run_preload_background(app) -> None:
    """Fuehrt den Cache-Warmup im Hintergrund-Thread aus.

    Nutzt dieselbe Warmup-Logik wie der Scheduler (`warmup_all_steckbriefe`),
    damit Scheduler und manueller Refresh identisch vollstaendig laufen.
    """
    from studiengang_steckbriefe.services.steckbrief import warmup_all_steckbriefe

    _preload_status["done"] = 0
    _preload_status["total"] = 0
    _preload_status["errors"] = []

    def _on_progress(done: int, total: int) -> None:
        _preload_status["done"] = done
        _preload_status["total"] = total

    try:
        result = warmup_all_steckbriefe(app, on_progress=_on_progress)
        _preload_status["errors"] = result["errors"]
    finally:
        _preload_status["running"] = False


@cache_mgmt_bp.route("/api/cache/preload", methods=["POST"])
@admin_required
def preload():
    """Startet den Cache-Warmup asynchron im Hintergrund."""
    import threading

    from flask import current_app

    if _preload_status["running"]:
        return jsonify(
            success=True,
            message="Preload laeuft bereits",
            done=_preload_status["done"],
            total=_preload_status["total"],
        )

    _preload_status["running"] = True
    app = current_app._get_current_object()
    t = threading.Thread(target=_run_preload_background, args=(app,), daemon=True)
    t.start()

    return jsonify(
        success=True, message="Preload gestartet", studiengaenge=0, endpoints_loaded=0, errors=[]
    )


@cache_mgmt_bp.route("/api/cache/preload/status", methods=["GET"])
@admin_required
def preload_status():
    """Gibt den aktuellen Status des Preload-Vorgangs zurueck."""
    return jsonify(
        running=_preload_status["running"],
        done=_preload_status["done"],
        total=_preload_status["total"],
        errors=_preload_status["errors"],
    )


@cache_mgmt_bp.route("/api/config/reload", methods=["POST"])
@admin_required
def reload_config_endpoint():
    """Laedt die Konfiguration aus MariaDB neu und leert den Cache."""
    try:
        reload_config()
        from studiengang_steckbriefe.services.queries import init_queries

        init_queries()
        cache_clear()
        return jsonify(success=True, message="Konfiguration neu geladen, Cache geleert")
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500
