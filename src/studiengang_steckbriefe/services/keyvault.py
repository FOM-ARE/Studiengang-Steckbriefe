"""Azure Key Vault Integration - laedt Secrets zur Laufzeit."""

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def load_keyvault_secrets(app):
    """Laedt Secrets aus Azure Key Vault und setzt sie in app.config.

    Wird in der App Factory aufgerufen (ausser im Testing-Modus).
    Nutzt Service Principal (falls konfiguriert) oder DefaultAzureCredential.
    Schlaegt Key Vault fehl, wird gewarnt aber kein Fehler ausgeloest.
    """
    vault_url = app.config.get("AZURE_KEYVAULT_URL")
    if not vault_url:
        app.logger.info("Key Vault URL nicht gesetzt - ueberspringe Secret-Laden")
        return

    client_id = app.config.get("AZURE_CLIENT_ID")
    client_secret = app.config.get("AZURE_CLIENT_SECRET")
    tenant_id = app.config.get("AZURE_TENANT_ID")

    try:
        if all([client_id, client_secret, tenant_id]):
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            app.logger.info("Key Vault: nutze Service Principal Credentials")
        else:
            credential = DefaultAzureCredential(exclude_environment_credential=True)
            app.logger.info("Key Vault: nutze DefaultAzureCredential (Managed Identity)")

        client = SecretClient(vault_url=vault_url, credential=credential)

        # Flask Secret Key (optional - Fallback: FLASK_SECRET_KEY-Umgebungsvariable)
        try:
            app.config["SECRET_KEY"] = client.get_secret("flasksecretkey").value
        except Exception:
            app.logger.warning(
                "Secret 'flasksecretkey' nicht im Key Vault gefunden "
                "- nutze FLASK_SECRET_KEY-Umgebungsvariable"
            )

        # MariaDB Passwort
        app.config["MARIADB_PASSWORD"] = client.get_secret("mariadb-password").value

        # DWH Connection String (optional - falls SQL Auth statt Windows Auth)
        try:
            app.config["DWH_CONNECTION_STRING"] = client.get_secret("dwh-connection-string").value
        except Exception:
            pass  # Windows Auth benoetigt kein gespeichertes Secret

        # DWH User (optional - fuer SQL Auth)
        try:
            app.config["DWH_USER"] = client.get_secret("dwh-user").value
        except Exception:
            app.logger.warning("Secret 'dwh-user' nicht im Key Vault gefunden")

        app.logger.info("Key Vault Secrets erfolgreich geladen")

    except Exception as exc:
        app.logger.warning("Key Vault nicht erreichbar - App startet ohne Secrets: %s", exc)
