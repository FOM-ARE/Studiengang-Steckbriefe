"""Tests fuer services/keyvault.py."""
from unittest.mock import MagicMock, patch

import pytest

_CRED = "studiengang_steckbriefe.services.keyvault.ClientSecretCredential"
_CLIENT = "studiengang_steckbriefe.services.keyvault.SecretClient"


@pytest.fixture
def app_without_vault(app):
    app.config["AZURE_KEYVAULT_URL"] = ""
    return app


@pytest.fixture
def app_with_vault(app):
    app.config["AZURE_KEYVAULT_URL"] = "https://kv-test.vault.azure.net/"
    app.config["AZURE_CLIENT_ID"] = "client-id"
    app.config["AZURE_CLIENT_SECRET"] = "client-secret"
    app.config["AZURE_TENANT_ID"] = "tenant-id"
    return app


class TestLoadKeyvaultSecrets:
    def test_keine_url_wird_uebersprungen(self, app_without_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        load_keyvault_secrets(app_without_vault)

    def test_nutzt_client_secret_credential(self, app_with_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        mock_client = MagicMock()
        mock_client.get_secret.return_value = MagicMock(value="wert")
        with patch(_CRED) as mock_cred, patch(_CLIENT, return_value=mock_client):
            load_keyvault_secrets(app_with_vault)
            mock_cred.assert_called_once_with(
                tenant_id="tenant-id",
                client_id="client-id",
                client_secret="client-secret",
            )

    def test_laedt_flasksecretkey(self, app_with_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        mock_client = MagicMock()
        mock_client.get_secret.side_effect = lambda n: MagicMock(value=f"wert-{n}")
        with patch(_CRED), patch(_CLIENT, return_value=mock_client):
            load_keyvault_secrets(app_with_vault)
            assert app_with_vault.config["SECRET_KEY"] == "wert-flasksecretkey"

    def test_laedt_mariadb_password(self, app_with_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        mock_client = MagicMock()
        mock_client.get_secret.side_effect = lambda n: MagicMock(value=f"wert-{n}")
        with patch(_CRED), patch(_CLIENT, return_value=mock_client):
            load_keyvault_secrets(app_with_vault)
            assert app_with_vault.config["MARIADB_PASSWORD"] == "wert-mariadb-password"

    def test_laedt_dwh_passwort_und_setzt_sql_auth(self, app_with_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        mock_client = MagicMock()
        mock_client.get_secret.side_effect = lambda n: MagicMock(value=f"wert-{n}")
        with patch(_CRED), patch(_CLIENT, return_value=mock_client):
            load_keyvault_secrets(app_with_vault)
            assert app_with_vault.config["DWH_PASSWORD"] == "wert-dwh-user"
            assert app_with_vault.config["DWH_AUTHENTICATION"] == "SQL"

    def test_fehlende_einzelne_secrets_kein_fehler(self, app_with_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        mock_client = MagicMock()
        mock_client.get_secret.side_effect = Exception("Secret nicht gefunden")
        with patch(_CRED), patch(_CLIENT, return_value=mock_client):
            load_keyvault_secrets(app_with_vault)

    def test_vault_nicht_erreichbar_kein_absturz(self, app_with_vault):
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        with patch(_CRED, side_effect=Exception("Vault nicht erreichbar")):
            load_keyvault_secrets(app_with_vault)
