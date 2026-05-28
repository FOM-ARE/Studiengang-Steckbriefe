"""App Factory – erstellt und konfiguriert die Flask-Anwendung."""

import atexit
from datetime import timedelta

from flask import Flask
from flask_cors import CORS


def create_app(config_name: str | None = None) -> Flask:
    """Erstellt die Flask-App mit der angegebenen Konfiguration.

    Args:
        config_name: Name der Konfiguration ('development', 'production', 'testing').
                     Default: 'default' (= DevelopmentConfig).
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    config_name = config_name or "default"

    from studiengang_steckbriefe.config import config

    app.config.from_object(config[config_name])
    app.permanent_session_lifetime = timedelta(
        hours=app.config.get("PERMANENT_SESSION_LIFETIME_HOURS", 8)
    )

    # CORS
    CORS(app, supports_credentials=True, origins=app.config["CORS_ORIGINS"])

    # Key Vault Secrets laden (nicht im Testing-Modus)
    # WICHTIG: muss vor init_app() erfolgen, da init_app() SECRET_KEY validiert
    if config_name != "testing":
        from studiengang_steckbriefe.services.keyvault import load_keyvault_secrets

        load_keyvault_secrets(app)

    # Production-Validierung (nach Key Vault, da SECRET_KEY dort gesetzt wird)
    config_cls = config[config_name]
    if hasattr(config_cls, "init_app"):
        config_cls.init_app(app)

    # Datenbank-Pool initialisieren
    if config_name != "testing":
        from studiengang_steckbriefe.services.db_connector import init_pool

        init_pool(app)

    # Konfigurations-DB laden und SQL-Queries initialisieren
    if config_name != "testing":
        with app.app_context():
            try:
                from studiengang_steckbriefe.services.config_db import reload_config

                reload_config()

                from studiengang_steckbriefe.services.queries import init_queries

                init_queries()
                app.config["DB_INIT_ERROR"] = None
            except Exception as exc:
                import traceback

                app.logger.error(
                    "DB-Initialisierung fehlgeschlagen: %s\n%s", exc, traceback.format_exc()
                )
                app.config["DB_INIT_ERROR"] = str(exc)

    # Blueprints registrieren
    from studiengang_steckbriefe.web.auth import auth_bp
    from studiengang_steckbriefe.web.cache_mgmt import cache_mgmt_bp
    from studiengang_steckbriefe.web.debug import debug_bp
    from studiengang_steckbriefe.web.health import health_bp
    from studiengang_steckbriefe.web.steckbrief import steckbrief_bp
    from studiengang_steckbriefe.web.studiengaenge import studiengaenge_bp
    from studiengang_steckbriefe.web.users import users_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(studiengaenge_bp)
    app.register_blueprint(steckbrief_bp)
    app.register_blueprint(cache_mgmt_bp)
    app.register_blueprint(debug_bp)

    # Scheduler starten (nicht im Testing-Modus)
    if config_name != "testing":
        from studiengang_steckbriefe.services.scheduler import (
            init_scheduler,
            shutdown_scheduler,
        )

        init_scheduler(app)
        atexit.register(shutdown_scheduler)

    return app
