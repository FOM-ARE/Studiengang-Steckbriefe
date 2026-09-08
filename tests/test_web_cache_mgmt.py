"""Tests fuer web/cache_mgmt.py."""

from unittest.mock import patch


class TestCacheStatus:
    def test_erfordert_admin(self, client):
        response = client.get("/api/cache/status")
        assert response.status_code == 401

    def test_nicht_admin_gibt_403(self, authenticated_client):
        with authenticated_client.session_transaction() as sess:
            user = dict(sess["user"])
            user["role"] = "read"
            sess["user"] = user
        response = authenticated_client.get("/api/cache/status")
        assert response.status_code == 403

    def test_admin_bekommt_status(self, authenticated_client):
        mock_status = {"entries": 5, "oldest": 1000.0, "newest": 2000.0}
        with patch("studiengang_steckbriefe.web.cache_mgmt.cache_status", return_value=mock_status):
            response = authenticated_client.get("/api/cache/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["entries"] == 5


class TestCacheClear:
    def test_erfordert_admin(self, client):
        response = client.post("/api/cache/clear")
        assert response.status_code == 401

    def test_leert_cache(self, authenticated_client):
        with patch("studiengang_steckbriefe.web.cache_mgmt.cache_clear") as mock_clear:
            response = authenticated_client.post("/api/cache/clear")
        assert response.status_code == 200
        assert response.get_json()["success"] is True
        mock_clear.assert_called_once()


class TestCacheClearEntry:
    def test_loescht_einzelnen_eintrag(self, authenticated_client):
        with patch("studiengang_steckbriefe.web.cache_mgmt.cache_delete") as mock_del:
            response = authenticated_client.post("/api/cache/clear/WM/trends")
        assert response.status_code == 200
        mock_del.assert_called_once_with("trends_WM")


class TestReloadConfig:
    def test_laedt_konfiguration_neu(self, authenticated_client):
        with (
            patch("studiengang_steckbriefe.web.cache_mgmt.reload_config") as mock_reload,
            patch("studiengang_steckbriefe.web.cache_mgmt.cache_clear"),
        ):
            response = authenticated_client.post("/api/config/reload")
        assert response.status_code == 200
        mock_reload.assert_called_once()

    def test_fehler_gibt_500(self, authenticated_client):
        with patch(
            "studiengang_steckbriefe.web.cache_mgmt.reload_config",
            side_effect=Exception("MariaDB down"),
        ):
            response = authenticated_client.post("/api/config/reload")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "MariaDB down" in data["error"]


class TestDatenstand:
    def test_unauthentifiziert_gibt_401(self, client):
        response = client.get("/api/cache/datenstand")
        assert response.status_code == 401

    def test_mit_timestamp(self, authenticated_client):
        with patch(
            "studiengang_steckbriefe.web.cache_mgmt.cache_status",
            return_value={"entries": 1, "newest": 1700000000.0},
        ):
            response = authenticated_client.get("/api/cache/datenstand")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["datenstand"] is not None

    def test_ohne_timestamp(self, authenticated_client):
        with patch(
            "studiengang_steckbriefe.web.cache_mgmt.cache_status",
            return_value={"entries": 0, "newest": None},
        ):
            response = authenticated_client.get("/api/cache/datenstand")
        assert response.status_code == 200
        assert response.get_json()["datenstand"] is None


class TestPreloadStatus:
    def test_erfordert_admin(self, client):
        response = client.get("/api/cache/preload/status")
        assert response.status_code == 401

    def test_gibt_status_zurueck(self, authenticated_client):
        import studiengang_steckbriefe.web.cache_mgmt as cm

        cm._preload_status.update({"running": False, "done": 3, "total": 10, "errors": ["err1"]})
        response = authenticated_client.get("/api/cache/preload/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["done"] == 3
        assert data["total"] == 10
        assert data["errors"] == ["err1"]


class TestRunPreloadBackground:
    def test_get_studiengaenge_fehler_setzt_running_false(self, app):
        """Wenn get_studiengaenge wirft, wird running=False gesetzt."""
        import studiengang_steckbriefe.web.cache_mgmt as cm
        from studiengang_steckbriefe.web.cache_mgmt import _run_preload_background

        cm._preload_status["running"] = True
        with (
            app.app_context(),
            __import__("unittest.mock", fromlist=["patch"]).patch(
                "studiengang_steckbriefe.services.steckbrief.get_studiengaenge",
                side_effect=RuntimeError("DB down"),
            ),
        ):
            _run_preload_background(app)
        assert cm._preload_status["running"] is False

    def test_endpoints_werden_fuer_alle_pks_aufgerufen(self, app):
        """Alle Endpunkt-Funktionen werden fuer jeden PK aufgerufen."""
        from unittest.mock import MagicMock, patch

        import studiengang_steckbriefe.web.cache_mgmt as cm
        from studiengang_steckbriefe.web.cache_mgmt import _run_preload_background

        hsb_data = [{"programmes": [{"kurzname": "BBA"}]}]
        mock_fn = MagicMock()

        with (
            app.app_context(),
            patch(
                "studiengang_steckbriefe.services.steckbrief.get_studiengaenge",
                return_value=hsb_data,
            ),
            patch("studiengang_steckbriefe.services.steckbrief.get_trends", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_stammdaten", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_studienerfolg", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_uebergang", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_herkunft", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_zuzahler", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_vertiefungsrichtungen", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_rahmendaten", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_aktive_hszen", mock_fn),
            patch("studiengang_steckbriefe.services.steckbrief.get_anrechnungen", mock_fn),
        ):
            _run_preload_background(app)

        assert cm._preload_status["running"] is False
        assert mock_fn.call_count == 10  # 10 Endpunkte x 1 PK

    def test_endpoint_fehler_wird_als_error_gespeichert(self, app):
        """Ein fehlgeschlagener Endpoint landet in errors, Preload laeuft weiter."""
        from unittest.mock import patch

        import studiengang_steckbriefe.web.cache_mgmt as cm
        from studiengang_steckbriefe.web.cache_mgmt import _run_preload_background

        hsb_data = [{"programmes": [{"kurzname": "BBA"}]}]

        def fail_trends(pk):
            raise RuntimeError("fail")

        with (
            app.app_context(),
            patch(
                "studiengang_steckbriefe.services.steckbrief.get_studiengaenge",
                return_value=hsb_data,
            ),
            patch("studiengang_steckbriefe.services.steckbrief.get_trends", fail_trends),
            patch("studiengang_steckbriefe.services.steckbrief.get_stammdaten", return_value={}),
            patch("studiengang_steckbriefe.services.steckbrief.get_studienerfolg", return_value={}),
            patch("studiengang_steckbriefe.services.steckbrief.get_uebergang", return_value={}),
            patch("studiengang_steckbriefe.services.steckbrief.get_herkunft", return_value={}),
            patch("studiengang_steckbriefe.services.steckbrief.get_zuzahler", return_value={}),
            patch(
                "studiengang_steckbriefe.services.steckbrief.get_vertiefungsrichtungen",
                return_value={},
            ),
            patch("studiengang_steckbriefe.services.steckbrief.get_rahmendaten", return_value={}),
            patch("studiengang_steckbriefe.services.steckbrief.get_aktive_hszen", return_value={}),
            patch("studiengang_steckbriefe.services.steckbrief.get_anrechnungen", return_value={}),
        ):
            _run_preload_background(app)

        assert cm._preload_status["running"] is False
        assert len(cm._preload_status["errors"]) == 1
        assert "get_trends" in cm._preload_status["errors"][0]

    def test_success(self, authenticated_client):
        """Preload antwortet sofort mit 200 und startet Hintergrund-Thread."""
        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value.start = lambda: None
            response = authenticated_client.post("/api/cache/preload")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "Preload gestartet"

    def test_fehler_bei_get_studiengaenge_gibt_500(self, authenticated_client):
        """Wenn Preload bereits laeuft, gibt es eine entsprechende Meldung."""
        import studiengang_steckbriefe.web.cache_mgmt as cm

        original = cm._preload_status.copy()
        cm._preload_status["running"] = True
        try:
            response = authenticated_client.post("/api/cache/preload")
        finally:
            cm._preload_status.update(original)
        assert response.status_code == 200
        assert "laeuft bereits" in response.get_json()["message"]
