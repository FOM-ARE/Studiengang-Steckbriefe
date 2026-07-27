import os


def _azure_authority(tenant_id: str) -> str:
    """Baut die Entra Authority-URL aus der Tenant-ID."""
    if tenant_id:
        return f"https://login.microsoftonline.com/{tenant_id}"
    return "https://login.microsoftonline.com/common"


def _keyvault_url() -> str:
    """Ermittelt die Key Vault URL â€“ explizite Env-Var hat Vorrang, Fallback ueber APP_ENV."""
    explicit = os.environ.get("AZURE_KEYVAULT_URL", "")
    if explicit:
        return explicit
    mapping = {
        "development": "https://kv-sgsteckbriefe-dev.vault.azure.net/",
        "staging": "https://kv-sgsteckbriefe-stg.vault.azure.net/",
        "production": "https://kv-sgsteckbriefe-prd.vault.azure.net/",
    }
    return mapping.get(os.environ.get("APP_ENV", ""), "")


class Config:
    """Basis-Konfiguration. Werte werden per Umgebungsvariable ueberschrieben."""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
    DEBUG = False
    TESTING = False

    # DWH (SQL Server via pyodbc)
    DWH_HOST = os.environ.get("DWH_HOST", "ms-sql-107.bcw-intern.local")
    DWH_PORT = os.environ.get("DWH_PORT", "1433")
    DWH_DATABASE = os.environ.get("DWH_DATABASE", "BCW_DWH")
    DWH_AUTHENTICATION = os.environ.get("DWH_AUTHENTICATION", "SQL")
    DWH_USER = os.environ.get("DWH_USER") or "VSC_DWH_Only_Read"
    DWH_PASSWORD = os.environ.get("DWH_PASSWORD", "")

    # MariaDB (Konfigurations-DB)
    MARIADB_HOST = os.environ.get("DB_HOST", "mariadb-dev.bcw-intern.local")
    MARIADB_PORT = int(os.environ.get("DB_PORT", "3306"))
    MARIADB_USER = os.environ.get("DB_USER", "HochschulorgaApps")
    MARIADB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    MARIADB_DATABASE = os.environ.get("DB_NAME", "HochschulorgaApps")
    MARIADB_CHARSET = os.environ.get("DB_CHARSET", "utf8mb4")
    MARIADB_SSL = os.environ.get("DB_SSL", "true").lower() == "true"
    MARIADB_SSL_CA = os.environ.get("DB_SSL_CA", "")  # Pfad zum CA-Cert (leer = Self-Signed)

    # Azure Credentials (Service Principal â€“ fuer Key Vault UND Entra ID)
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")

    # Azure Key Vault (APP_ENV-basierter Fallback wenn AZURE_KEYVAULT_URL nicht gesetzt)
    AZURE_KEYVAULT_URL = _keyvault_url()

    # Entra ID (MSAL) â€“ gleicher Service Principal wie Key Vault
    ENTRA_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
    ENTRA_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
    ENTRA_AUTHORITY = _azure_authority(os.environ.get("AZURE_TENANT_ID", ""))
    ENTRA_REDIRECT_URI = os.environ.get(
        "ENTRA_REDIRECT_URI", "http://localhost:5000/api/auth/callback"
    )
    # Entra ID Gruppen (Object-IDs fuer Token-Claims-basierte Rollenzuordnung)
    ENTRA_GROUP_ADMIN = os.environ.get("ENTRA_GROUP_ADMIN", "2392116c-4f38-4a3b-aaf3-87c5709328b1")
    ENTRA_GROUP_WRITE = os.environ.get("ENTRA_GROUP_WRITE", "2f306242-4c19-43a8-bc4c-a4cfff907015")
    ENTRA_GROUP_READ = os.environ.get("ENTRA_GROUP_READ", "c7380f69-3a73-4f22-add5-99ec4833afb2")

    # Berechtigungs-DB (SQL Server BCW_STA – eigener User nur fuer Berechtigungstabelle)
    PERM_DWH_HOST = os.environ.get("PERM_DWH_HOST", "ms-sql-107.bcw-intern.local")
    PERM_DWH_PORT = os.environ.get("PERM_DWH_PORT", "1433")
    PERM_DWH_DATABASE = os.environ.get("PERM_DWH_DATABASE", "BCW_STA")
    PERM_DWH_USER = os.environ.get("PERM_DWH_USER", "App.SG_Steckbriefe")
    PERM_DWH_PASSWORD = os.environ.get("PERM_DWH_PASSWORD", "")
    PERM_DWH_AUTHENTICATION = os.environ.get("PERM_DWH_AUTHENTICATION", "SQL")
    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:8000").split(",")

    # App
    APP_NAME = "Studiengang-Steckbriefe"
    PERMANENT_SESSION_LIFETIME_HOURS = 8


class DevelopmentConfig(Config):
    DEBUG = True

    # Pipeline liefert: AZURE_CLIENT_ID_DEV, AZURE_CLIENT_SECRET_DEV, AZURE_TENANT_ID_DEV
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID_DEV", os.environ.get("AZURE_CLIENT_ID", ""))
    AZURE_CLIENT_SECRET = os.environ.get(
        "AZURE_CLIENT_SECRET_DEV", os.environ.get("AZURE_CLIENT_SECRET", "")
    )
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID_DEV", os.environ.get("AZURE_TENANT_ID", ""))
    ENTRA_CLIENT_ID = AZURE_CLIENT_ID
    ENTRA_CLIENT_SECRET = AZURE_CLIENT_SECRET
    ENTRA_AUTHORITY = _azure_authority(AZURE_TENANT_ID)
    ENTRA_REDIRECT_URI = "https://studiengangsteckbriefe-dev.srvs.bcw-intern.local/auth/callback"


class StagingConfig(Config):
    DEBUG = False

    # Pipeline: AZURE_CLIENT_ID_STAGING, AZURE_CLIENT_SECRET_STAGING, AZURE_TENANT_ID_STAGING
    AZURE_CLIENT_ID = os.environ.get(
        "AZURE_CLIENT_ID_STAGING", os.environ.get("AZURE_CLIENT_ID", "")
    )
    AZURE_CLIENT_SECRET = os.environ.get(
        "AZURE_CLIENT_SECRET_STAGING", os.environ.get("AZURE_CLIENT_SECRET", "")
    )
    AZURE_TENANT_ID = os.environ.get(
        "AZURE_TENANT_ID_STAGING", os.environ.get("AZURE_TENANT_ID", "")
    )
    ENTRA_CLIENT_ID = AZURE_CLIENT_ID
    ENTRA_CLIENT_SECRET = AZURE_CLIENT_SECRET
    ENTRA_AUTHORITY = _azure_authority(AZURE_TENANT_ID)


class ProductionConfig(Config):
    DEBUG = False

    # Pipeline liefert: AZURE_CLIENT_ID_PROD, AZURE_CLIENT_SECRET_PROD, AZURE_TENANT_ID_PROD
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID_PROD", os.environ.get("AZURE_CLIENT_ID", ""))
    AZURE_CLIENT_SECRET = os.environ.get(
        "AZURE_CLIENT_SECRET_PROD", os.environ.get("AZURE_CLIENT_SECRET", "")
    )
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID_PROD", os.environ.get("AZURE_TENANT_ID", ""))
    ENTRA_CLIENT_ID = AZURE_CLIENT_ID
    ENTRA_CLIENT_SECRET = AZURE_CLIENT_SECRET
    ENTRA_AUTHORITY = _azure_authority(AZURE_TENANT_ID)

    @classmethod
    def init_app(cls, app):
        """Validiert kritische Konfigurationswerte in Produktion."""
        if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "dev-secret-key":
            raise RuntimeError("SECRET_KEY muss in Produktion gesetzt sein")
        if not app.config.get("AZURE_KEYVAULT_URL"):
            raise RuntimeError("AZURE_KEYVAULT_URL muss in Produktion gesetzt sein")
        if not app.config.get("AZURE_CLIENT_ID"):
            raise RuntimeError("AZURE_CLIENT_ID muss in Produktion gesetzt sein")
        if not app.config.get("AZURE_TENANT_ID"):
            raise RuntimeError("AZURE_TENANT_ID muss in Produktion gesetzt sein")


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    DWH_HOST = "localhost"
    MARIADB_HOST = "localhost"
    AZURE_CLIENT_ID = "test-client-id"
    AZURE_CLIENT_SECRET = "test-client-secret"
    AZURE_TENANT_ID = "test-tenant-id"
    ENTRA_CLIENT_ID = "test-client-id"
    ENTRA_CLIENT_SECRET = "test-client-secret"
    ENTRA_AUTHORITY = "https://login.microsoftonline.com/test-tenant-id"


config = {
    "development": DevelopmentConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
