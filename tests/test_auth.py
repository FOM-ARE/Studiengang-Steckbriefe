"""Tests fuer Auth-Endpoints."""


def test_me_unauthenticated(client):
    """Nicht-authentifizierter User bekommt 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    data = response.get_json()
    assert data["authenticated"] is False


def test_me_authenticated(authenticated_client):
    """Authentifizierter User bekommt 200 mit User-Info."""
    response = authenticated_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.get_json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == "test.user"


def test_logout(authenticated_client):
    """Logout leert die Session."""
    response = authenticated_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    # Nach Logout nicht mehr authentifiziert
    response = authenticated_client.get("/api/auth/me")
    assert response.status_code == 401


def test_login_redirects(client):
    """Login-Endpoint leitet zu Microsoft weiter (oder gibt Fehler bei fehlender Config)."""
    response = client.get("/api/auth/login")
    # Ohne gueltige Entra-Config gibt es einen Redirect oder Fehler
    assert response.status_code in (302, 500)
