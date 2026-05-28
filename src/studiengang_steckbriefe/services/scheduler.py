"""APScheduler 4.x Integration fuer geplante Cache-Reloads."""

from apscheduler import Scheduler
from apscheduler.triggers.cron import CronTrigger

from studiengang_steckbriefe.services.cache import cache_clear

_scheduler: Scheduler | None = None


def scheduled_cache_reload():
    """Leert den Cache (wird vom Scheduler taeglich aufgerufen)."""
    print("[Scheduler] Cache-Reload gestartet...")
    cache_clear()
    print("[Scheduler] Cache geleert.")


def init_scheduler(app):
    """Initialisiert den APScheduler 4.x mit einem taeglichen Cache-Reload-Job."""
    global _scheduler

    _scheduler = Scheduler()
    _scheduler.add_schedule(
        scheduled_cache_reload,
        CronTrigger(hour=3, minute=0),
        id="daily_cache_reload",
    )
    _scheduler.start_in_background()
    app.logger.info("Scheduler gestartet (Cache-Reload taeglich um 03:00)")


def shutdown_scheduler():
    """Stoppt den Scheduler sauber."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
