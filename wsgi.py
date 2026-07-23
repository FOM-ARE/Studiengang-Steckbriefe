"""Einstiegspunkt fuer die Studiengang-Steckbriefe Anwendung."""

import logging
import os
import sys
import traceback

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Umgebungsspezifische .env-Datei laden (Fallback: .env)
# FLASK_CONFIG hat Vorrang, APP_ENV wird als Fallback genutzt (gesetzt durch Mirantis-Template)
_env_name = os.environ.get("FLASK_CONFIG") or os.environ.get("APP_ENV", "development")
_env_file = f".env.{_env_name}"
if os.path.isfile(_env_file):
    load_dotenv(_env_file)
else:
    load_dotenv()

config_name = os.environ.get("FLASK_CONFIG") or os.environ.get("APP_ENV", "default")
logger.info("Starting app with config=%s", config_name)

_startup_error = None

try:
    from studiengang_steckbriefe.web import create_app

    app = create_app(config_name)
    logger.info("App created successfully")
except Exception:
    _startup_error = traceback.format_exc()
    logger.critical("FATAL: App konnte nicht gestartet werden:\n%s", _startup_error)

    # Minimaler Fallback-Server damit der Container nicht crasht
    # und der Fehler ueber /api/health abrufbar ist.
    # Alle Endpoints sind GET-only und aendern keinen Zustand –
    # CSRF-Schutz ist fuer diese read-only Fehler-Endpoints nicht erforderlich.
    from flask import Flask, jsonify

    app = Flask(__name__)  # NOSONAR: S4502 – GET-only error endpoints, no CSRF risk
    _error_msg = _startup_error

    @app.route("/api/health", methods=["GET"])
    def health_fallback():
        return jsonify(
            status="error",
            stage="startup",
            flask_config=config_name,
            traceback=_error_msg,
        ), 503

    @app.route("/", defaults={"path": ""}, methods=["GET"])
    @app.route("/<path:path>", methods=["GET"])
    def catch_all(path):
        return jsonify(status="error", message="App startup failed", traceback=_error_msg), 503


if __name__ == "__main__":
    if "--production" in sys.argv:
        from waitress import serve

        serve(app, host="0.0.0.0", port=8080)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
