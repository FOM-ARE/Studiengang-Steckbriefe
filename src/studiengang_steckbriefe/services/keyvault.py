"""Azure Key Vault Integration – laedt Secrets zur Laufzeit."""

from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient


def load_keyvault_secrets(app):
    """Laedt Secrets aus Azure Key Vault und setzt sie in app.config.

    Wird in der App Factory aufgerufen (ausser im Testing-Modus).
    Nutzt die per Pipeline bereitgestellten Azure-Credentials
    (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID).
    """
    vault_url = app.config.get("AZURE_KEYVAULT_URL")
    if not vault_url:
        app.logger.info("Key Vault URL nicht gesetzt – ueberspringe Secret-Laden")
        return

    client_id = app.config.get("AZURE_CLIENT_ID")
    client_secret = app.config.get("AZURE_CLIENT_SECRET")
    tenant_id = app.config.get("AZURE_TENANT_ID")

    if not all([client_id, client_secret, tenant_id]):
        app.logger.warning(
            "Azure-Credentials unvollstaendig – Key Vault kann nicht erreicht werden"
        )
        return

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    client = SecretClient(vault_url=vault_url, credential=credential)

    # Flask Secret Key (optional – Fallback: FLASK_SECRET_KEY-Umgebungsvariable)
    try:
        app.config["SECRET_KEY"] = client.get_secret("flasksecretkey").value
    except Exception:
        app.logger.warning(
            "Secret 'flasksecretkey' nicht im Key Vault gefunden "
            "– nutze FLASK_SECRET_KEY-Umgebungsvariable"
        )

    # MariaDB Passwort
    app.config["MARIADB_PASSWORD"] = client.get_secret("mariadb-password").value

    # DWH Connection String (optional – falls SQL Auth statt Windows Auth)
    try:
        app.config["DWH_CONNECTION_STRING"] = client.get_secret("dwh-connection-string").value
    except Exception:
        pass  # Windows Auth benoetigt kein gespeichertes Secret

    app.logger.info("Key Vault Secrets erfolgreich geladen")
