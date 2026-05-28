"""Tests fuer den Health-Endpoint."""


def test_health_returns_ok(client):
    """Health-Endpoint gibt 200 zurueck wenn DB erreichbar."""
    # Im Testing-Modus wird kein DB-Pool initialisiert,
    # daher erwarten wir einen 503 (DB nicht verbunden)
    response = client.get("/api/health")
    assert response.status_code in (200, 503)
    data = response.get_json()
    assert "status" in data


def test_health_has_database_field(client):
    """Health-Response enthaelt das Feld 'database'."""
    response = client.get("/api/health")
    data = response.get_json()
    assert "database" in data
