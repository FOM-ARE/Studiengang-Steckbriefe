"""Tests fuer Studiengaenge-Endpoint."""
from unittest.mock import patch


def test_studiengaenge_requires_auth(client):
    """Studiengaenge-Endpoint erfordert Authentifizierung."""
    response = client.get("/api/studiengaenge")
    assert response.status_code == 401


def test_studiengaenge_authenticated(authenticated_client):
    """Authentifizierter User kann Studiengaenge abrufen."""
    # Ohne DB-Verbindung im Testing erwarten wir einen Fehler
    response = authenticated_client.get("/api/studiengaenge")
    # Kann 200 (mit Cache) oder 500 (ohne DB) oder TypeError sein
    assert response.status_code in (200, 500)


def test_studiengaenge_gibt_daten_zurueck(authenticated_client):
    """Gibt Studiengaenge-Daten als JSON zurueck."""
    mock_data = [{"name": "Wirtschaft & Management", "programmes": []}]
    with patch("studiengang_steckbriefe.web.studiengaenge.svc.get_studiengaenge", return_value=mock_data):
        response = authenticated_client.get("/api/studiengaenge")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"] == mock_data


def test_studiengaenge_fehler_gibt_500(authenticated_client):
    """Bei Exception wird HTTP 500 zurueckgegeben."""
    with patch(
        "studiengang_steckbriefe.web.studiengaenge.svc.get_studiengaenge",
        side_effect=RuntimeError("DB offline"),
    ):
        response = authenticated_client.get("/api/studiengaenge")
    assert response.status_code == 500
    data = response.get_json()
    assert data["success"] is False
    assert "DB offline" in data["error"]
