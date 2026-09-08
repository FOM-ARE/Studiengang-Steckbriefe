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
        assert sched_mod._scheduler_thread.name == "weekly-cache-reload"


class TestNextRunTime:
    def test_naechster_sonntag_07(self):
        """_next_run_time gibt den naechsten Sonntag 07:00 zurueck."""
        from datetime import datetime

        # Mittwoch 2026-09-09 10:00 -> naechster Sonntag = 2026-09-13 07:00
        result = sched_mod._next_run_time(datetime(2026, 9, 9, 10, 0))
        assert result == datetime(2026, 9, 13, 7, 0)

    def test_sonntag_vor_07_ist_heute(self):
        """Sonntag frueh vor 07:00 -> Reload heute 07:00."""
        from datetime import datetime

        result = sched_mod._next_run_time(datetime(2026, 9, 13, 6, 0))
        assert result == datetime(2026, 9, 13, 7, 0)

    def test_sonntag_nach_07_ist_naechste_woche(self):
        """Sonntag nach 07:00 -> Reload naechsten Sonntag."""
        from datetime import datetime

        result = sched_mod._next_run_time(datetime(2026, 9, 13, 8, 0))
        assert result == datetime(2026, 9, 20, 7, 0)


class TestWarmupCache:
    def test_warmup_ruft_warmup_all_auf(self, app):
        """_warmup_cache delegiert an warmup_all_steckbriefe."""
        import studiengang_steckbriefe.services.scheduler as sched_mod

        sched_mod._flask_app = app
        with patch(
            "studiengang_steckbriefe.services.steckbrief.warmup_all_steckbriefe",
            return_value={"total": 10, "done": 10, "errors": []},
        ) as mock_warmup:
            sched_mod._warmup_cache()
        mock_warmup.assert_called_once_with(app)

    def test_warmup_schluckt_exception(self, app):
        """_warmup_cache wirft keine Exception wenn warmup_all_steckbriefe fehlschlaegt."""
        import studiengang_steckbriefe.services.scheduler as sched_mod

        sched_mod._flask_app = app
        with patch(
            "studiengang_steckbriefe.services.steckbrief.warmup_all_steckbriefe",
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
