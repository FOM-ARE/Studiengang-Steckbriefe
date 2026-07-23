"""Threading-basierter Scheduler fuer geplante Cache-Reloads.

Ersetzt APScheduler (GHSA-9cfw-f3f9-7mm7 / CVE-2026-31072) durch
Pythons eingebautes threading-Modul.
"""

import threading
from datetime import datetime, timedelta

from studiengang_steckbriefe.services.cache import cache_clear

_stop_event: threading.Event | None = None
_scheduler_thread: threading.Thread | None = None
_flask_app = None


def _warmup_cache() -> None:
    """Befuellt den Cache mit den Studiengaengen (Startseite)."""
    from studiengang_steckbriefe.services.steckbrief import get_studiengaenge

    with _flask_app.app_context():
        try:
            data = get_studiengaenge()
            print(f"[Scheduler] Cache-Warmup: {len(data)} Hochschulbereiche geladen.")
        except Exception as exc:
            print(f"[Scheduler] Cache-Warmup fehlgeschlagen: {exc}")


def scheduled_cache_reload() -> None:
    """Leert den Cache und befuellt ihn neu (wird vom Scheduler taeglich aufgerufen)."""
    print("[Scheduler] Cache-Reload gestartet...")
    cache_clear()
    print("[Scheduler] Cache geleert.")
    _warmup_cache()


def _run_scheduler(stop_event: threading.Event) -> None:
    """Laeuft im Hintergrund-Thread und fuehrt den Cache-Reload taeglich um 05:30 aus."""
    while not stop_event.is_set():
        now = datetime.now()
        next_run = now.replace(hour=5, minute=30, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - datetime.now()).total_seconds()
        stop_event.wait(timeout=wait_seconds)
        if not stop_event.is_set():
            try:
                scheduled_cache_reload()
            except Exception as exc:
                print(f"[Scheduler] Fehler beim Cache-Reload: {exc}")


def init_scheduler(app) -> None:
    """Startet den Hintergrund-Thread fuer taegliche Cache-Reloads um 05:30."""
    global _stop_event, _scheduler_thread, _flask_app
    _flask_app = app
    _stop_event = threading.Event()
    _scheduler_thread = threading.Thread(
        target=_run_scheduler,
        args=(_stop_event,),
        daemon=True,
        name="daily-cache-reload",
    )
    _scheduler_thread.start()
    app.logger.info("Scheduler gestartet (Cache-Reload taeglich um 05:30)")


def shutdown_scheduler() -> None:
    """Stoppt den Scheduler sauber."""
    global _stop_event, _scheduler_thread
    if _stop_event:
        _stop_event.set()
        _stop_event = None
    _scheduler_thread = None
