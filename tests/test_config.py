"""Tests fuer config.py - Konfigurationsklassen und Hilfsfunktionen."""
import os
from unittest.mock import patch

import pytest

from studiengang_steckbriefe.config import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    StagingConfig,
    TestingConfig,
    _azure_authority,
    _keyvault_url,
    config,
)


class TestAzureAuthority:
    def test_mit_tenant_id(self):
        url = _azure_authority("abc-123")
        assert url == "https://login.microsoftonline.com/abc-123"

    def test_ohne_tenant_id(self):
        url = _azure_authority("")
        assert url == "https://login.microsoftonline.com/common"


class TestKeyvaultUrl:
    def test_explizite_env_var_hat_vorrang(self):
        with patch.dict(os.environ, {"AZURE_KEYVAULT_URL": "https://mein-kv.vault.azure.net/"}):
            assert _keyvault_url() == "https://mein-kv.vault.azure.net/"

    def test_fallback_staging(self):
        saved = os.environ.pop("AZURE_KEYVAULT_URL", None)
        try:
            with patch.dict(os.environ, {"APP_ENV": "staging"}):
                url = _keyvault_url()
            assert "stg" in url
        finally:
            if saved:
                os.environ["AZURE_KEYVAULT_URL"] = saved

    def test_unbekannte_env_gibt_leer_zurueck(self):
        saved = os.environ.pop("AZURE_KEYVAULT_URL", None)
        try:
            with patch.dict(os.environ, {"APP_ENV": "unbekannt"}):
                url = _keyvault_url()
            assert url == ""
        finally:
            if saved:
                os.environ["AZURE_KEYVAULT_URL"] = saved


class TestConfig:
    def test_defaults(self):
        assert Config.DEBUG is False
        assert Config.TESTING is False
        assert Config.DWH_DATABASE == "BCW_DWH"
        assert Config.MARIADB_PORT == 3306

    def test_dwh_user_fallback(self):
        assert Config.DWH_USER != ""


class TestTestingConfig:
    def test_testing_flag(self):
        assert TestingConfig.TESTING is True

    def test_secret_key_gesetzt(self):
        assert TestingConfig.SECRET_KEY == "test-secret-key"

    def test_entra_konfiguration(self):
        assert TestingConfig.ENTRA_CLIENT_ID == "test-client-id"
        assert TestingConfig.ENTRA_AUTHORITY == "https://login.microsoftonline.com/test-tenant-id"


class TestDevelopmentConfig:
    def test_debug_aktiv(self):
        assert DevelopmentConfig.DEBUG is True

    def test_testing_inaktiv(self):
        assert DevelopmentConfig.TESTING is False


class TestStagingConfig:
    def test_debug_inaktiv(self):
        assert StagingConfig.DEBUG is False


class TestProductionConfig:
    def test_debug_inaktiv(self):
        assert ProductionConfig.DEBUG is False

    def test_init_app_kein_secret_key(self, app):
        app.config["SECRET_KEY"] = "dev-secret-key"
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            ProductionConfig.init_app(app)

    def test_init_app_kein_keyvault_url(self, app):
        app.config["SECRET_KEY"] = "echter-key"
        app.config["AZURE_KEYVAULT_URL"] = ""
        with pytest.raises(RuntimeError, match="AZURE_KEYVAULT_URL"):
            ProductionConfig.init_app(app)

    def test_init_app_kein_client_id(self, app):
        app.config["SECRET_KEY"] = "echter-key"
        app.config["AZURE_KEYVAULT_URL"] = "https://kv.vault.azure.net/"
        app.config["AZURE_CLIENT_ID"] = ""
        with pytest.raises(RuntimeError, match="AZURE_CLIENT_ID"):
            ProductionConfig.init_app(app)

    def test_init_app_kein_tenant_id(self, app):
        app.config["SECRET_KEY"] = "echter-key"
        app.config["AZURE_KEYVAULT_URL"] = "https://kv.vault.azure.net/"
        app.config["AZURE_CLIENT_ID"] = "mein-client"
        app.config["AZURE_TENANT_ID"] = ""
        with pytest.raises(RuntimeError, match="AZURE_TENANT_ID"):
            ProductionConfig.init_app(app)


class TestConfigMapping:
    def test_alle_keys_vorhanden(self):
        assert "development" in config
        assert "staging" in config
        assert "production" in config
        assert "testing" in config
        assert "default" in config

    def test_testing_key_zeigt_auf_testing_config(self):
        assert config["testing"] is TestingConfig