"""Tests fuer web/main.py (Main-Blueprint)."""


class TestIndexRoute:
    def test_unauthentifiziert_redirect_zu_login(self, client):
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_authentifiziert_gibt_200(self, authenticated_client):
        response = authenticated_client.get("/")
        assert response.status_code == 200

    def test_login_seite_erreichbar(self, client):
        response = client.get("/login")
        assert response.status_code == 200
