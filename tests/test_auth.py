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


def test_login_success_redirect_zu_microsoft(client):
    """Login leitet bei gueltiger Konfiguration zu Microsoft weiter."""
    from unittest.mock import MagicMock, patch

    mock_auth = MagicMock()
    mock_auth.get_auth_url.return_value = "https://login.microsoftonline.com/auth"
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        response = client.get("/api/auth/login")
    assert response.status_code == 302
    assert "login.microsoftonline.com" in response.headers["Location"]


def test_callback_state_mismatch_redirect(client):
    """Callback mit falschem State leitet zur Login-Seite."""
    with client.session_transaction() as sess:
        sess["auth_state"] = "correct-state"
    response = client.get("/auth/callback?state=wrong-state&code=abc")
    assert response.status_code == 302
    assert "invalid_state" in response.headers["Location"]


def test_callback_kein_code_redirect(client):
    """Callback ohne Code leitet zur Login-Seite."""
    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    response = client.get("/auth/callback?state=state-abc")
    assert response.status_code == 302
    assert "auth_failed" in response.headers["Location"]


def test_callback_value_error_redirect(client):
    """Callback mit ValueError beim Token-Exchange leitet zur Login-Seite."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.side_effect = ValueError("Token abgelaufen")
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        response = client.get("/auth/callback?state=state-abc&code=xyz")
    assert response.status_code == 302
    assert "auth_failed" in response.headers["Location"]


def test_callback_exception_redirect(client):
    """Callback mit unerwarteter Exception leitet zur Login-Seite."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.side_effect = RuntimeError("Netzwerkfehler")
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        response = client.get("/auth/callback?state=state-abc&code=xyz")
    assert response.status_code == 302
    assert "auth_failed" in response.headers["Location"]


def test_callback_keine_rolle_redirect(client):
    """Callback ohne Gruppe und ohne DB-Berechtigung leitet zur Login-Seite."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.return_value = {
        "id_token_claims": {"preferred_username": "no.role@fom.de", "name": "No Role"}
    }
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        with patch(
            "studiengang_steckbriefe.web.auth.get_role_from_token_claims", return_value=None
        ):
            with patch("studiengang_steckbriefe.web.auth.get_user_role", return_value=None):
                response = client.get("/auth/callback?state=state-abc&code=xyz")
    assert response.status_code == 302
    assert "no_permission" in response.headers["Location"]


def test_callback_ruft_graph_api_wenn_kein_groups_claim(client):
    """Wenn groups-Claim fehlt, werden Gruppen via Graph API geholt."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.return_value = {
        "id_token_claims": {
            "preferred_username": "christian.rosenberger@fom.de",
            "name": "Christian",
        },
        "access_token": "graph-access-token",
    }
    mock_auth.fetch_user_groups.return_value = ["2392116c-4f38-4a3b-aaf3-87c5709328b1"]

    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        with patch(
            "studiengang_steckbriefe.web.auth.get_role_from_token_claims",
            side_effect=lambda claims, mapping: (
                "admin"
                if "2392116c-4f38-4a3b-aaf3-87c5709328b1" in claims.get("groups", [])
                else None
            ),
        ):
            response = client.get("/auth/callback?state=state-abc&code=xyz")

    mock_auth.fetch_user_groups.assert_called_once_with("graph-access-token")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user"]["role"] == "admin"


def test_callback_kein_access_token_kein_graph_api_call(client):
    """Wenn kein access_token vorhanden, wird Graph API nicht aufgerufen."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.return_value = {
        "id_token_claims": {"preferred_username": "user@fom.de", "name": "User"},
        # kein access_token
    }
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        with patch(
            "studiengang_steckbriefe.web.auth.get_role_from_token_claims", return_value=None
        ):
            with patch("studiengang_steckbriefe.web.auth.get_user_role", return_value="read"):
                response = client.get("/auth/callback?state=state-abc&code=xyz")

    mock_auth.fetch_user_groups.assert_not_called()
    assert response.status_code == 302


def test_callback_erfolgreicher_login_via_gruppe(client):
    """Erfolgreicher Callback via Gruppen-Claim setzt die Session."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.return_value = {
        "id_token_claims": {
            "preferred_username": "anna.muster@fom.de",
            "name": "Anna Muster",
            "groups": ["2392116c-4f38-4a3b-aaf3-87c5709328b1"],
        }
    }
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        with patch(
            "studiengang_steckbriefe.web.auth.get_role_from_token_claims", return_value="admin"
        ):
            response = client.get("/auth/callback?state=state-abc&code=xyz")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user"]["role"] == "admin"
        assert sess["user"]["username"] == "anna.muster"


def test_callback_erfolgreicher_login_via_db_fallback(client):
    """Erfolgreicher Callback via DB-Fallback wenn kein Gruppen-Claim."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.return_value = {
        "id_token_claims": {"preferred_username": "bob.read@fom.de", "name": "Bob"}
    }
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        with patch(
            "studiengang_steckbriefe.web.auth.get_role_from_token_claims", return_value=None
        ):
            with patch("studiengang_steckbriefe.web.auth.get_user_role", return_value="read"):
                response = client.get("/auth/callback?state=state-abc&code=xyz")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user"]["role"] == "read"


def test_callback_db_fehler_redirect(client):
    """Callback mit DB-Fehler beim Fallback leitet zur Login-Seite."""
    from unittest.mock import MagicMock, patch

    with client.session_transaction() as sess:
        sess["auth_state"] = "state-abc"
    mock_auth = MagicMock()
    mock_auth.acquire_token.return_value = {
        "id_token_claims": {"preferred_username": "user@fom.de", "name": "User"}
    }
    with patch("studiengang_steckbriefe.web.auth.EntraIdAuth", return_value=mock_auth):
        with patch(
            "studiengang_steckbriefe.web.auth.get_role_from_token_claims", return_value=None
        ):
            with patch(
                "studiengang_steckbriefe.web.auth.get_user_role",
                side_effect=Exception("DB down"),
            ):
                response = client.get("/auth/callback?state=state-abc&code=xyz")
    assert response.status_code == 302
    assert "db_error" in response.headers["Location"]
