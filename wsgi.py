"""Einstiegspunkt fuer die Studiengang-Steckbriefe Anwendung."""

import json
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

    # Minimaler WSGI-Fallback (kein Flask) damit der Container nicht crasht
    # und der Fehler ueber /api/health abrufbar ist.
    _error_payload = json.dumps(
        {
            "status": "error",
            "stage": "startup",
            "flask_config": config_name,
            "traceback": _startup_error,
        }
    ).encode("utf-8")
    _generic_payload = json.dumps({"status": "error", "message": "App startup failed"}).encode(
        "utf-8"
    )

    def app(environ, start_response):  # type: ignore[misc]
        path = environ.get("PATH_INFO", "")
        body = _error_payload if path == "/api/health" else _generic_payload
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        start_response("503 Service Unavailable", headers)
        return [body]


if __name__ == "__main__":
    if "--production" in sys.argv:
        from waitress import serve

        serve(app, host="0.0.0.0", port=8080)
    else:
        from werkzeug.serving import run_simple

        run_simple("0.0.0.0", 5000, app, use_reloader=False, use_debugger=False)
