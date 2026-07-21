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
