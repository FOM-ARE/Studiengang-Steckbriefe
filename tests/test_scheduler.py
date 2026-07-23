"""Tests fuer services/scheduler.py."""

from unittest.mock import patch

import pytest

import studiengang_steckbriefe.services.scheduler as sched_mod
from studiengang_steckbriefe.services.scheduler import (
    init_scheduler,
    scheduled_cache_reload,
    shutdown_scheduler,
)


@pytest.fixture(autouse=True)
def stop_after_test():
    yield
    shutdown_scheduler()


class TestScheduledCacheReload:
    def test_leert_cache(self):
        with (
            patch("studiengang_steckbriefe.services.scheduler.cache_clear") as mock_clear,
            patch("studiengang_steckbriefe.services.scheduler._warmup_cache"),
        ):
            scheduled_cache_reload()
            mock_clear.assert_called_once()


class TestInitScheduler:
    def test_startet_thread(self, app):
        init_scheduler(app)
        assert sched_mod._scheduler_thread is not None
        assert sched_mod._scheduler_thread.is_alive()

    def test_thread_ist_daemon(self, app):
        init_scheduler(app)
        assert sched_mod._scheduler_thread.daemon is True

    def test_thread_name(self, app):
        init_scheduler(app)
        assert sched_mod._scheduler_thread.name == "daily-cache-reload"


class TestShutdownScheduler:
    def test_shutdown_setzt_stop_event(self, app):
        init_scheduler(app)
        assert sched_mod._stop_event is not None
        shutdown_scheduler()
        assert sched_mod._stop_event is None

    def test_shutdown_ohne_vorherigen_start_kein_fehler(self):
        shutdown_scheduler()
