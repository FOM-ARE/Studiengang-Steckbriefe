"""Tests fuer web/debug.py (Debug-Endpoints)."""
from unittest.mock import patch

_QDB = "studiengang_steckbriefe.web.debug.query_db"


class TestDebugAuthSchutz:
    def test_semester_format_erfordert_auth(self, client):
        assert client.get("/api/debug/semester-format").status_code == 401

    def test_produktkuerzel_erfordert_auth(self, client):
        assert client.get("/api/debug/produktkuerzel").status_code == 401


class TestDebugSemesterFormat:
    def test_gibt_daten_zurueck(self, authenticated_client):
        mock_rows = [{"Semesterkuerzel": "2025-WS"}, {"Semesterkuerzel": "2025-SS"}]
        with patch(_QDB, return_value=mock_rows):
            response = authenticated_client.get("/api/debug/semester-format")
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_db_fehler_gibt_500(self, authenticated_client):
        with patch(_QDB, side_effect=Exception("DB nicht erreichbar")):
            response = authenticated_client.get("/api/debug/semester-format")
        assert response.status_code == 500
        assert response.get_json()["success"] is False


class TestDebugProduktkuerzel:
    def test_gibt_daten_zurueck(self, authenticated_client):
        mock_rows = [{"Produktkuerzel": "WM", "Studiengang": "Wirtschaft", "Hochschulbereich": "W"}]
        with patch(_QDB, return_value=mock_rows):
            response = authenticated_client.get("/api/debug/produktkuerzel")
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_db_fehler_gibt_500(self, authenticated_client):
        with patch(_QDB, side_effect=Exception("Timeout")):
            response = authenticated_client.get("/api/debug/produktkuerzel")
        assert response.status_code == 500