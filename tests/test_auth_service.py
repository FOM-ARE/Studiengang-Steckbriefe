"""Tests fuer services/auth.py (EntraIdAuth + Berechtigungen)."""

from unittest.mock import MagicMock, patch

import pytest

from studiengang_steckbriefe.services.auth import (
    get_user_role,
    is_authenticated,
    load_app_permissions,
)

_MSAL_CCA = "studiengang_steckbriefe.services.auth.msal.ConfidentialClientApplication"


class TestEntraIdAuth:
    def test_initialisierung(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        with patch(_MSAL_CCA) as mock_msal:
            with app.app_context():
                EntraIdAuth(app)
            mock_msal.assert_called_once_with(
                "test-client-id",
                authority="https://login.microsoftonline.com/test-tenant-id",
                client_credential="test-client-secret",
            )

    def test_get_auth_url(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        with patch(_MSAL_CCA) as mock_msal:
            mock_instance = MagicMock()
            mock_instance.get_authorization_request_url.return_value = (
                "https://login.microsoft.com/auth"
            )
            mock_msal.return_value = mock_instance
            with app.app_context():
                auth = EntraIdAuth(app)
                url = auth.get_auth_url(state="test-state")
            assert url == "https://login.microsoft.com/auth"

    def test_acquire_token_erfolgreich(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        with patch(_MSAL_CCA) as mock_msal:
            mock_instance = MagicMock()
            mock_instance.acquire_token_by_authorization_code.return_value = {
                "id_token_claims": {"preferred_username": "test@fom.de", "name": "Test"}
            }
            mock_msal.return_value = mock_instance
            with app.app_context():
                auth = EntraIdAuth(app)
                result = auth.acquire_token("auth-code-123")
            assert "id_token_claims" in result

    def test_acquire_token_fehler_wirft_value_error(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        with patch(_MSAL_CCA) as mock_msal:
            mock_instance = MagicMock()
            mock_instance.acquire_token_by_authorization_code.return_value = {
                "error": "invalid_grant",
                "error_description": "Token abgelaufen",
            }
            mock_msal.return_value = mock_instance
            with app.app_context():
                auth = EntraIdAuth(app)
                with pytest.raises(ValueError, match="Token abgelaufen"):
                    auth.acquire_token("ungültiger-code")


class TestLoadAppPermissions:
    def test_gibt_berechtigungen_zurueck(self, app):
        mock_rows = [
            {"Berechtigt": "max.mustermann", "Recht": "read", "Typ": "user"},
            {"Berechtigt": "admin.user", "Recht": "admin", "Typ": "user"},
        ]
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth.mariadb_connector.query",
                return_value=mock_rows,
            ):
                perms = load_app_permissions()
        assert "read" in perms
        assert "admin" in perms
        assert any(e["berechtigt"] == "max.mustermann" for e in perms["read"])


class TestGetUserRole:
    def test_gibt_hoechste_rolle_zurueck(self, app):
        mock_rows = [
            {"Berechtigt": "test.user", "Recht": "read", "Typ": "user"},
            {"Berechtigt": "test.user", "Recht": "admin", "Typ": "user"},
        ]
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth.mariadb_connector.query",
                return_value=mock_rows,
            ):
                role = get_user_role("test.user")
        assert role == "admin"

    def test_gibt_none_zurueck_wenn_kein_eintrag(self, app):
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth.mariadb_connector.query",
                return_value=[],
            ):
                role = get_user_role("unbekannt")
        assert role is None

    def test_case_insensitive(self, app):
        mock_rows = [{"Berechtigt": "TEST.USER", "Recht": "write", "Typ": "user"}]
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth.mariadb_connector.query",
                return_value=mock_rows,
            ):
                role = get_user_role("test.user")
        assert role == "write"


class TestIsAuthenticated:
    def test_nicht_eingeloggt(self, client):
        with client.application.test_request_context("/"):
            assert is_authenticated() is False
