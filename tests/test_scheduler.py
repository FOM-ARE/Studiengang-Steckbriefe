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


class TestWarmupCache:
    def test_warmup_laedt_studiengaenge(self, app):
        """_warmup_cache ruft get_studiengaenge im App-Context auf."""
        import studiengang_steckbriefe.services.scheduler as sched_mod

        sched_mod._flask_app = app
        with patch(
            "studiengang_steckbriefe.services.steckbrief.get_studiengaenge",
            return_value=[{"name": "WM"}],
        ) as mock_get:
            sched_mod._warmup_cache()
        mock_get.assert_called_once()

    def test_warmup_schluckt_exception(self, app):
        """_warmup_cache wirft keine Exception wenn get_studiengaenge fehlschlaegt."""
        import studiengang_steckbriefe.services.scheduler as sched_mod

        sched_mod._flask_app = app
        with patch(
            "studiengang_steckbriefe.services.steckbrief.get_studiengaenge",
            side_effect=RuntimeError("DB down"),
        ):
            sched_mod._warmup_cache()  # darf nicht werfen


class TestRunScheduler:
    def test_fuehrt_reload_aus_wenn_nicht_gestoppt(self, app):
        """_run_scheduler fuehrt scheduled_cache_reload aus wenn stop_event nicht gesetzt."""
        import threading

        import studiengang_steckbriefe.services.scheduler as sched_mod

        stop_event = threading.Event()
        calls = []

        def fake_reload():
            calls.append(1)
            stop_event.set()  # nach erstem Aufruf stoppen

        with (
            patch("studiengang_steckbriefe.services.scheduler.scheduled_cache_reload", fake_reload),
            patch.object(stop_event, "wait", lambda timeout=None: None),
        ):
            sched_mod._run_scheduler(stop_event)

        assert len(calls) == 1

    def test_fehler_im_reload_wird_abgefangen(self, app):
        """_run_scheduler laeuft weiter wenn scheduled_cache_reload eine Exception wirft."""
        import threading

        import studiengang_steckbriefe.services.scheduler as sched_mod

        stop_event = threading.Event()
        call_count = [0]

        def fail_once():
            call_count[0] += 1
            stop_event.set()
            raise RuntimeError("Reload-Fehler")

        with (
            patch("studiengang_steckbriefe.services.scheduler.scheduled_cache_reload", fail_once),
            patch.object(stop_event, "wait", lambda timeout=None: None),
        ):
            sched_mod._run_scheduler(stop_event)  # darf nicht werfen

        assert call_count[0] == 1

    def test_shutdown_ohne_vorherigen_start_kein_fehler(self):
        shutdown_scheduler()
