"""Tests fuer web/__init__.py (create_app) - non-testing Pfade."""

from unittest.mock import patch


class TestCreateAppNonTesting:
    """Testet die create_app-Pfade die im testing-Modus uebersprungen werden."""

    def _make_app(self, config_name="development", reload_side_effect=None):
        """Hilfsmethode: create_app mit gemockten externen Abhaengigkeiten."""
        from studiengang_steckbriefe.web import create_app

        with (
            patch("studiengang_steckbriefe.services.keyvault.load_keyvault_secrets") as mock_kv,
            patch("studiengang_steckbriefe.services.db_connector.init_pool") as mock_pool,
            patch(
                "studiengang_steckbriefe.services.config_db.reload_config",
                side_effect=reload_side_effect,
            ) as mock_reload,
            patch("studiengang_steckbriefe.services.queries.init_queries") as mock_queries,
            patch("studiengang_steckbriefe.services.scheduler.init_scheduler") as mock_sched,
            patch("studiengang_steckbriefe.services.scheduler.shutdown_scheduler"),
        ):
            app = create_app(config_name)
            return app, mock_kv, mock_pool, mock_reload, mock_queries, mock_sched

    def test_keyvault_wird_geladen(self):
        app, mock_kv, _, _, _, _ = self._make_app()
        mock_kv.assert_called_once_with(app)

    def test_db_pool_wird_initialisiert(self):
        app, _, mock_pool, _, _, _ = self._make_app()
        mock_pool.assert_called_once_with(app)

    def test_config_db_und_queries_werden_initialisiert(self):
        _, _, _, mock_reload, mock_queries, _ = self._make_app()
        mock_reload.assert_called_once()
        mock_queries.assert_called_once()

    def test_db_init_error_ist_none_bei_erfolg(self):
        app, _, _, _, _, _ = self._make_app()
        assert app.config.get("DB_INIT_ERROR") is None

    def test_db_init_error_wird_gesetzt_bei_fehler(self):
        app, _, _, _, _, _ = self._make_app(
            reload_side_effect=Exception("Verbindung fehlgeschlagen")
        )
        assert "Verbindung fehlgeschlagen" in app.config.get("DB_INIT_ERROR", "")

    def test_scheduler_wird_gestartet(self):
        app, _, _, _, _, mock_sched = self._make_app()
        mock_sched.assert_called_once_with(app)

    def test_testing_modus_ladet_keyvault_nicht(self):
        from studiengang_steckbriefe.web import create_app

        with patch("studiengang_steckbriefe.services.keyvault.load_keyvault_secrets") as mock_kv:
            create_app("testing")
        mock_kv.assert_not_called()

    def test_testing_modus_startet_scheduler_nicht(self):
        from studiengang_steckbriefe.web import create_app

        with patch("studiengang_steckbriefe.services.scheduler.init_scheduler") as mock_sched:
            create_app("testing")
        mock_sched.assert_not_called()
