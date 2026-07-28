"""Tests fuer web/steckbrief.py (Steckbrief-Endpoints)."""

from unittest.mock import patch

_SVC = "studiengang_steckbriefe.web.steckbrief.svc"

ENDPOINTS = [
    "/api/steckbrief/WM/trends",
    "/api/steckbrief/WM/stammdaten",
    "/api/steckbrief/WM/studienerfolg",
    "/api/steckbrief/WM/anrechnungen",
    "/api/steckbrief/WM/uebergang",
    "/api/steckbrief/WM/herkunft",
    "/api/steckbrief/WM/zuzahler",
    "/api/steckbrief/WM/vertiefungsrichtungen",
    "/api/steckbrief/WM/rahmendaten",
    "/api/steckbrief/WM/hszen",
]


class TestAuthSchutz:
    def test_alle_endpoints_erfordern_auth(self, client):
        for endpoint in ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} erwartet 401"


class TestTrends:
    def test_gibt_daten_zurueck(self, authenticated_client):
        mock_data = {"semester": [], "studierende": []}
        with patch(f"{_SVC}.get_trends", return_value=mock_data):
            response = authenticated_client.get("/api/steckbrief/WM/trends")
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_service_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_trends", side_effect=Exception("DB-Fehler")):
            response = authenticated_client.get("/api/steckbrief/WM/trends")
        assert response.status_code == 500


class TestStammdaten:
    def test_gibt_daten_zurueck(self, authenticated_client):
        with patch(f"{_SVC}.get_stammdaten", return_value={}):
            response = authenticated_client.get("/api/steckbrief/WM/stammdaten")
        assert response.status_code == 200


class TestRadmendaten:
    def test_gibt_daten_zurueck(self, authenticated_client):
        mock_data = {"ue": {}, "ueBySemester": {}, "zeitmodelle": []}
        with patch(f"{_SVC}.get_rahmendaten", return_value=mock_data):
            response = authenticated_client.get("/api/steckbrief/WM/rahmendaten")
        assert response.status_code == 200

    def test_service_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_rahmendaten", side_effect=RuntimeError("Fehler")):
            response = authenticated_client.get("/api/steckbrief/WM/rahmendaten")
        assert response.status_code == 500


class TestWeitereEndpoints:
    def test_studienerfolg(self, authenticated_client):
        with patch(f"{_SVC}.get_studienerfolg", return_value={}):
            assert authenticated_client.get("/api/steckbrief/WM/studienerfolg").status_code == 200

    def test_studienerfolg_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_studienerfolg", side_effect=Exception("Fehler")):
            assert authenticated_client.get("/api/steckbrief/WM/studienerfolg").status_code == 500

    def test_anrechnungen(self, authenticated_client):
        with patch(f"{_SVC}.get_anrechnungen", return_value={}):
            assert authenticated_client.get("/api/steckbrief/WM/anrechnungen").status_code == 200

    def test_anrechnungen_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_anrechnungen", side_effect=Exception("Fehler")):
            assert authenticated_client.get("/api/steckbrief/WM/anrechnungen").status_code == 500

    def test_uebergang(self, authenticated_client):
        with patch(f"{_SVC}.get_uebergang", return_value={}):
            assert authenticated_client.get("/api/steckbrief/WM/uebergang").status_code == 200

    def test_uebergang_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_uebergang", side_effect=Exception("Fehler")):
            assert authenticated_client.get("/api/steckbrief/WM/uebergang").status_code == 500

    def test_herkunft(self, authenticated_client):
        with patch(f"{_SVC}.get_herkunft", return_value={}):
            assert authenticated_client.get("/api/steckbrief/WM/herkunft").status_code == 200

    def test_herkunft_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_herkunft", side_effect=Exception("Fehler")):
            assert authenticated_client.get("/api/steckbrief/WM/herkunft").status_code == 500

    def test_zuzahler(self, authenticated_client):
        with patch(f"{_SVC}.get_zuzahler", return_value={}):
            assert authenticated_client.get("/api/steckbrief/WM/zuzahler").status_code == 200

    def test_zuzahler_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_zuzahler", side_effect=Exception("Fehler")):
            assert authenticated_client.get("/api/steckbrief/WM/zuzahler").status_code == 500

    def test_vertiefungsrichtungen(self, authenticated_client):
        with patch(f"{_SVC}.get_vertiefungsrichtungen", return_value={}):
            r = authenticated_client.get("/api/steckbrief/WM/vertiefungsrichtungen")
            assert r.status_code == 200

    def test_vertiefungsrichtungen_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_vertiefungsrichtungen", side_effect=Exception("Fehler")):
            r = authenticated_client.get("/api/steckbrief/WM/vertiefungsrichtungen")
            assert r.status_code == 500

    def test_hszen(self, authenticated_client):
        with patch(f"{_SVC}.get_aktive_hszen", return_value=[]):
            assert authenticated_client.get("/api/steckbrief/WM/hszen").status_code == 200

    def test_hszen_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_aktive_hszen", side_effect=Exception("Fehler")):
            assert authenticated_client.get("/api/steckbrief/WM/hszen").status_code == 500


class TestStammdatenFehler:
    def test_service_fehler_gibt_500(self, authenticated_client):
        with patch(f"{_SVC}.get_stammdaten", side_effect=Exception("DB-Fehler")):
            response = authenticated_client.get("/api/steckbrief/WM/stammdaten")
        assert response.status_code == 500
