"""Einstiegspunkt fuer die Studiengang-Steckbriefe Anwendung."""

import os
import sys

from dotenv import load_dotenv

# Umgebungsspezifische .env-Datei laden (Fallback: .env)
_env_name = os.environ.get("FLASK_CONFIG", "development")
_env_file = f".env.{_env_name}"
if os.path.isfile(_env_file):
    load_dotenv(_env_file)
else:
    load_dotenv()

import logging
import traceback

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

try:
    from studiengang_steckbriefe.web import create_app  # noqa: E402

    config_name = os.environ.get("FLASK_CONFIG", "default")
    logger.info("Starting app with FLASK_CONFIG=%s", config_name)
    app = create_app(config_name)
    logger.info("App created successfully")
except Exception:
    logger.critical("FATAL: App konnte nicht gestartet werden:\n%s", traceback.format_exc())
    sys.exit(1)

if __name__ == "__main__":
    if "--production" in sys.argv:
        from waitress import serve

        serve(app, host="0.0.0.0", port=8080)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
