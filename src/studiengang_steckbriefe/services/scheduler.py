"""Threading-basierter Scheduler fuer geplante Cache-Reloads.

Ersetzt APScheduler (GHSA-9cfw-f3f9-7mm7 / CVE-2026-31072) durch
Pythons eingebautes threading-Modul.

Der Cache wird **einmal pro Woche sonntags um 07:00** komplett neu aufgebaut.
Waehrend der Woche laufen tagsueber keine On-Demand-Ladungen mehr; nur beim
manuellen Refresh einer einzelnen Seite (siehe `web/cache_mgmt.py`) wird
gezielt neu geladen.
"""

import threading
from datetime import datetime, timedelta

from studiengang_steckbriefe.services.cache import cache_clear

# Sonntag = 6 (Montag = 0)
_RELOAD_WEEKDAY = 6
_RELOAD_HOUR = 7
_RELOAD_MINUTE = 0

_stop_event: threading.Event | None = None
_scheduler_thread: threading.Thread | None = None
_flask_app = None


def _next_run_time(now: datetime) -> datetime:
    """Berechnet den naechsten Reload-Zeitpunkt (Sonntag 07:00)."""
    days_ahead = (_RELOAD_WEEKDAY - now.weekday()) % 7
    candidate = now.replace(
        hour=_RELOAD_HOUR, minute=_RELOAD_MINUTE, second=0, microsecond=0
    ) + timedelta(days=days_ahead)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def _warmup_cache() -> None:
    """Befuellt den Cache vollstaendig: alle Steckbriefe fuer alle Studiengaenge."""
    from studiengang_steckbriefe.services.steckbrief import warmup_all_steckbriefe

    try:
        result = warmup_all_steckbriefe(_flask_app)
    except Exception as exc:
        print(f"[Scheduler] Cache-Warmup fehlgeschlagen: {exc}")
        return

    print(
        f"[Scheduler] Cache-Warmup: {result['done']}/{result['total']} Endpunkte geladen "
        f"({len(result['errors'])} Fehler)."
    )


def scheduled_cache_reload() -> None:
    """Leert den Cache und befuellt ihn neu (wird vom Scheduler woechentlich aufgerufen)."""
    print("[Scheduler] Cache-Reload gestartet...")
    cache_clear()
    print("[Scheduler] Cache geleert.")
    _warmup_cache()


def _run_scheduler(stop_event: threading.Event) -> None:
    """Laeuft im Hintergrund-Thread und fuehrt den Cache-Reload sonntags um 07:00 aus."""
    while not stop_event.is_set():
        next_run = _next_run_time(datetime.now())
        wait_seconds = (next_run - datetime.now()).total_seconds()
        stop_event.wait(timeout=wait_seconds)
        if not stop_event.is_set():
            try:
                scheduled_cache_reload()
            except Exception as exc:
                print(f"[Scheduler] Fehler beim Cache-Reload: {exc}")


def init_scheduler(app) -> None:
    """Startet den Hintergrund-Thread fuer woechentliche Cache-Reloads (Sonntag 07:00)."""
    global _stop_event, _scheduler_thread, _flask_app
    _flask_app = app
    _stop_event = threading.Event()
    _scheduler_thread = threading.Thread(
        target=_run_scheduler,
        args=(_stop_event,),
        daemon=True,
        name="weekly-cache-reload",
    )
    _scheduler_thread.start()
    app.logger.info("Scheduler gestartet (Cache-Reload sonntags um 07:00)")


def shutdown_scheduler() -> None:
    """Stoppt den Scheduler sauber."""
    global _stop_event, _scheduler_thread
    if _stop_event:
        _stop_event.set()
        _stop_event = None
    _scheduler_thread = None
