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
        mock_cursor = MagicMock()
        mock_cursor.description = [("Berechtigt",), ("Recht",), ("Typ",)]
        mock_cursor.fetchall.return_value = [
            ("max.mustermann", "read", "user"),
            ("admin.user", "admin", "user"),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                perms = load_app_permissions()
        assert "read" in perms
        assert "admin" in perms
        assert any(e["berechtigt"] == "max.mustermann" for e in perms["read"])


class TestGetUserRole:
    def _mock_perm_conn(self, rows):
        mock_cursor = MagicMock()
        mock_cursor.description = [("Berechtigt",), ("Recht",), ("Typ",)]
        mock_cursor.fetchall.return_value = rows
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    def test_gibt_hoechste_rolle_zurueck(self, app):
        mock_conn = self._mock_perm_conn(
            [
                ("test.user", "read", "user"),
                ("test.user", "admin", "user"),
            ]
        )
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role("test.user")
        assert role == "admin"

    def test_gibt_none_zurueck_wenn_kein_eintrag(self, app):
        mock_conn = self._mock_perm_conn([])
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role("unbekannt")
        assert role is None

    def test_case_insensitive(self, app):
        mock_conn = self._mock_perm_conn([("TEST.USER", "write", "user")])
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role("test.user")
        assert role == "write"

    def test_gruppe_in_db_ergibt_rolle(self, app):
        """Gruppen-Object-ID in DB und user_groups stimmen ueberein → Rolle wird erkannt."""
        mock_conn = self._mock_perm_conn(
            [("2392116c-4f38-4a3b-aaf3-87c5709328b1", "admin", "gruppe")]
        )
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role(
                    "christian.rosenberger",
                    user_groups=["2392116c-4f38-4a3b-aaf3-87c5709328b1"],
                )
        assert role == "admin"

    def test_gruppe_in_db_per_object_id(self, app):
        mock_conn = self._mock_perm_conn(
            [("2392116c-4f38-4a3b-aaf3-87c5709328b1", "admin", "gruppe")]
        )
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role(
                    "christian.rosenberger",
                    user_groups=["2392116c-4f38-4a3b-aaf3-87c5709328b1"],
                )
        assert role == "admin"

    def test_gruppen_pruefen_hoechste_rolle(self, app):
        mock_conn = self._mock_perm_conn(
            [
                ("c7380f69-3a73-4f22-add5-99ec4833afb2", "read", "gruppe"),
                ("2f306242-4c19-43a8-bc4c-a4cfff907015", "write", "gruppe"),
            ]
        )
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role(
                    "some.user",
                    user_groups=[
                        "c7380f69-3a73-4f22-add5-99ec4833afb2",
                        "2f306242-4c19-43a8-bc4c-a4cfff907015",
                    ],
                )
        assert role == "write"

    def test_keine_gruppe_kein_user_eintrag_gibt_none(self, app):
        mock_conn = self._mock_perm_conn([("andere.person", "admin", "user")])
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role(
                    "christian.rosenberger",
                    user_groups=["unbekannte-gruppe"],
                )
        assert role is None

    def test_user_eintrag_hat_vorrang_vor_gruppe(self, app):
        """Ein User-Eintrag mit admin schlaegt eine Gruppen-Berechtigung write."""
        mock_conn = self._mock_perm_conn(
            [
                ("christian.rosenberger", "admin", "user"),
                ("c7380f69-3a73-4f22-add5-99ec4833afb2", "read", "gruppe"),
            ]
        )
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                role = get_user_role(
                    "christian.rosenberger",
                    user_groups=["c7380f69-3a73-4f22-add5-99ec4833afb2"],
                )
        assert role == "admin"


class TestFetchUserGroups:
    def test_gibt_gruppen_ids_zurueck(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "2392116c-4f38-4a3b-aaf3-87c5709328b1"},
                {"id": "c7380f69-3a73-4f22-add5-99ec4833afb2"},
            ]
        }
        with patch(_MSAL_CCA):
            with patch(
                "studiengang_steckbriefe.services.auth.requests.get",
                return_value=mock_response,
            ):
                with app.app_context():
                    auth = EntraIdAuth(app)
                    groups = auth.fetch_user_groups("access-token-xyz")
        assert "2392116c-4f38-4a3b-aaf3-87c5709328b1" in groups
        assert "c7380f69-3a73-4f22-add5-99ec4833afb2" in groups

    def test_paginierung_folgt_next_link(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        first_response = MagicMock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "value": [{"id": "gruppe-1"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/memberOf?$skiptoken=abc",
        }
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.json.return_value = {"value": [{"id": "gruppe-2"}]}

        with patch(_MSAL_CCA):
            with patch(
                "studiengang_steckbriefe.services.auth.requests.get",
                side_effect=[first_response, second_response],
            ):
                with app.app_context():
                    auth = EntraIdAuth(app)
                    groups = auth.fetch_user_groups("access-token-xyz")
        assert "gruppe-1" in groups
        assert "gruppe-2" in groups

    def test_http_fehler_gibt_leere_liste(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        with patch(_MSAL_CCA):
            with patch(
                "studiengang_steckbriefe.services.auth.requests.get",
                return_value=mock_response,
            ):
                with app.app_context():
                    auth = EntraIdAuth(app)
                    groups = auth.fetch_user_groups("access-token-xyz")
        assert groups == []

    def test_netzwerkfehler_gibt_leere_liste(self, app):
        from studiengang_steckbriefe.services.auth import EntraIdAuth

        with patch(_MSAL_CCA):
            with patch(
                "studiengang_steckbriefe.services.auth.requests.get",
                side_effect=ConnectionError("Timeout"),
            ):
                with app.app_context():
                    auth = EntraIdAuth(app)
                    groups = auth.fetch_user_groups("access-token-xyz")
        assert groups == []


class TestIsAuthenticated:
    def test_nicht_eingeloggt(self, client):
        with client.application.test_request_context("/"):
            assert is_authenticated() is False

    def test_eingeloggt(self, authenticated_client):
        with authenticated_client.application.test_request_context("/"):
            with authenticated_client.session_transaction() as sess:
                sess["user"] = {"username": "test"}
            with authenticated_client.application.test_request_context("/"):
                # Direkt testen ueber die Session
                pass
        # Einfacher Test: authenticated_client hat user in Session
        response = authenticated_client.get("/api/auth/me")
        assert response.status_code == 200


class TestGetRoleFromTokenClaims:
    def test_gibt_admin_rolle_zurueck(self, app):
        from studiengang_steckbriefe.services.auth import get_role_from_token_claims

        claims = {"groups": ["2392116c-4f38-4a3b-aaf3-87c5709328b1"]}
        mapping = {
            "2392116c-4f38-4a3b-aaf3-87c5709328b1": "admin",
            "2f306242-4c19-43a8-bc4c-a4cfff907015": "write",
            "c7380f69-3a73-4f22-add5-99ec4833afb2": "read",
        }
        role = get_role_from_token_claims(claims, mapping)
        assert role == "admin"

    def test_gibt_hoechste_rolle_bei_mehreren_gruppen(self, app):
        from studiengang_steckbriefe.services.auth import get_role_from_token_claims

        claims = {
            "groups": [
                "c7380f69-3a73-4f22-add5-99ec4833afb2",
                "2f306242-4c19-43a8-bc4c-a4cfff907015",
            ]
        }
        mapping = {
            "2392116c-4f38-4a3b-aaf3-87c5709328b1": "admin",
            "2f306242-4c19-43a8-bc4c-a4cfff907015": "write",
            "c7380f69-3a73-4f22-add5-99ec4833afb2": "read",
        }
        role = get_role_from_token_claims(claims, mapping)
        assert role == "write"

    def test_keine_gruppen_im_claim_gibt_none(self, app):
        from studiengang_steckbriefe.services.auth import get_role_from_token_claims

        claims = {}
        mapping = {"abc": "admin"}
        role = get_role_from_token_claims(claims, mapping)
        assert role is None

    def test_keine_passende_gruppe_gibt_none(self, app):
        from studiengang_steckbriefe.services.auth import get_role_from_token_claims

        claims = {"groups": ["unbekannte-gruppe-id"]}
        mapping = {"bekannte-gruppe-id": "admin"}
        role = get_role_from_token_claims(claims, mapping)
        assert role is None

    def test_leerer_group_id_wird_ignoriert(self, app):
        from studiengang_steckbriefe.services.auth import get_role_from_token_claims

        claims = {"groups": ["valid-id"]}
        mapping = {"": "admin", "valid-id": "read"}
        role = get_role_from_token_claims(claims, mapping)
        assert role == "read"


class TestGetPermConnection:
    def test_baut_sql_connection_string(self, app):
        from unittest.mock import patch

        with app.app_context():
            app.config["PERM_DWH_AUTHENTICATION"] = "SQL"
            app.config["PERM_DWH_HOST"] = "sql-server"
            app.config["PERM_DWH_PORT"] = "1433"
            app.config["PERM_DWH_DATABASE"] = "BCW_STA"
            app.config["PERM_DWH_USER"] = "sa"
            app.config["PERM_DWH_PASSWORD"] = "secret"
            from studiengang_steckbriefe.services import auth as auth_svc

            with patch("studiengang_steckbriefe.services.auth.pyodbc.drivers", return_value=[]):
                with patch("studiengang_steckbriefe.services.auth.pyodbc.connect") as mock_connect:
                    auth_svc._get_perm_connection()
            conn_str = mock_connect.call_args[0][0]
        assert "UID=sa" in conn_str
        assert "BCW_STA" in conn_str

    def test_baut_windows_connection_string(self, app):
        from unittest.mock import patch

        with app.app_context():
            app.config["PERM_DWH_AUTHENTICATION"] = "Windows"
            app.config["PERM_DWH_HOST"] = "sql-server"
            app.config["PERM_DWH_PORT"] = "1433"
            app.config["PERM_DWH_DATABASE"] = "BCW_STA"
            from studiengang_steckbriefe.services import auth as auth_svc

            with patch("studiengang_steckbriefe.services.auth.pyodbc.drivers", return_value=[]):
                with patch("studiengang_steckbriefe.services.auth.pyodbc.connect") as mock_connect:
                    auth_svc._get_perm_connection()
            conn_str = mock_connect.call_args[0][0]
        assert "Trusted_Connection=yes" in conn_str


class TestCheckPermission:
    def _mock_conn(self, rows):
        mock_cursor = MagicMock()
        mock_cursor.description = [("Berechtigt",), ("Recht",), ("Typ",)]
        mock_cursor.fetchall.return_value = rows
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    def test_user_hat_berechtigung(self, app):
        from studiengang_steckbriefe.services.auth import check_permission

        mock_conn = self._mock_conn([("anna.muster", "read", "user")])
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                result = check_permission("anna.muster", "read")
        assert result is True

    def test_user_hat_keine_berechtigung(self, app):
        from studiengang_steckbriefe.services.auth import check_permission

        mock_conn = self._mock_conn([("other.user", "read", "user")])
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                result = check_permission("anna.muster", "read")
        assert result is False

    def test_leere_berechtigungen_gibt_false(self, app):
        from studiengang_steckbriefe.services.auth import check_permission

        mock_conn = self._mock_conn([])
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.auth._get_perm_connection",
                return_value=mock_conn,
            ):
                result = check_permission("anna.muster")
        assert result is False


class TestGetCurrentUser:
    def test_gibt_user_aus_session(self, authenticated_client):
        from studiengang_steckbriefe.services.auth import get_current_user

        with authenticated_client.application.test_request_context("/"):
            from flask import session

            session["user"] = {"username": "test.user", "role": "admin"}
            user = get_current_user()
        assert user["username"] == "test.user"

    def test_gibt_none_wenn_nicht_eingeloggt(self, client):
        from studiengang_steckbriefe.services.auth import get_current_user

        with client.application.test_request_context("/"):
            user = get_current_user()
        assert user is None
