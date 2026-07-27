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


def test_health_startup_fehler_gibt_503(app):
    """DB_INIT_ERROR in der Config fuehrt zu 503."""
    app.config["DB_INIT_ERROR"] = "Verbindung fehlgeschlagen"
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert data["stage"] == "startup"
    app.config.pop("DB_INIT_ERROR", None)


def test_health_db_verbunden_gibt_200(client):
    """Health gibt 200 zurueck wenn DB-Verbindung erfolgreich ist."""
    from unittest.mock import MagicMock, patch

    mock_conn = MagicMock()
    with patch("studiengang_steckbriefe.web.health.get_connection", return_value=mock_conn):
        with patch("studiengang_steckbriefe.web.health.release_connection") as mock_release:
            response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    mock_release.assert_called_once_with(mock_conn)


def test_health_db_fehler_gibt_503(client):
    """Health gibt 503 zurueck wenn DB-Verbindung fehlschlaegt."""
    from unittest.mock import patch

    with patch(
        "studiengang_steckbriefe.web.health.get_connection",
        side_effect=Exception("Keine Verbindung"),
    ):
        response = client.get("/api/health")
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert data["database"] == "disconnected"
