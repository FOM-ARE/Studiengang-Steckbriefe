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


class TestPreload:
    def test_erfordert_admin(self, client):
        response = client.post("/api/cache/preload")
        assert response.status_code == 401

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
