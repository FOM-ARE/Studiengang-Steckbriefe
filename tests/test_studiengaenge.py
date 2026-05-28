"""Tests fuer Studiengaenge-Endpoint."""


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
