"""DWH-API Connector - Laedt Studierende-Daten aus der DWH-API statt Direct-DB.

Dieser Service ersetzt die direkten SQL-Abfragen auf BCW_DWH.dwh.C_Studierendenzahlen
mit Calls zur DWH-API (https://datawarehouseapi.srvs.bcw-intern.local/api/v1/gesamtstudierende).

Die API reduziert Netzwerktraffic (80-90% Ersparnis) und DB-Last erheblich.
Authentifizierung: X-API-Key Header (geladen aus Azure Key Vault als "DWH-API").
"""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class DWHAPIConnector:
    """Connector zur DWH-API fuer Gesamtstudierende und Studiengang-Daten."""

    BASE_URL = "https://datawarehouseapi.srvs.bcw-intern.local/api/v1"
    TIMEOUT = 15

    def __init__(self, api_key: str | None = None):
        """
        Initialisiert den Connector.

        Args:
            api_key: X-API-Key fuer Authentifizierung. Falls None, wird versucht,
                     ihn aus Flask app.config zu laden.
        """
        self.api_key = api_key
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        """Lazy-load: Session mit API-Key Header."""
        if self._session is None:
            self._session = requests.Session()
            if self.api_key:
                self._session.headers.update({"X-API-Key": self.api_key})
        return self._session

    def _api_call(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Macht API-Call und gibt Antwort zurueck.

        Args:
            endpoint: z.B. 'gesamtstudierende'
            params: Query-Parameter (z.B. {'Semester': '2026-WS', 'gruppierung': 'Semester'})

        Returns:
            Vollstaendige API-Response (dict mit 'filter', 'gruppierung', 'werte')

        Raises:
            requests.RequestException: Bei Verbindungs-/Authentifizierungsfehler
            ValueError: Bei invalid JSON-Response
        """
        url = f"{self.BASE_URL}/{endpoint}"
        session = self._get_session()

        try:
            response = session.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            logger.error("DWH-API Verbindungsfehler: %s", e)
            raise
        except requests.exceptions.Timeout as e:
            logger.error("DWH-API Timeout nach %ds: %s", self.TIMEOUT, e)
            raise
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error("DWH-API: Nicht autorisiert (X-API-Key ungueltig oder fehlt)")
            elif response.status_code == 300:
                logger.warning("DWH-API: Wartungszeitfenster aktiv (HTTP 300)")
            elif response.status_code == 400:
                logger.error("DWH-API: Ungueltige Anfrage - %s", response.text)
            else:
                logger.error("DWH-API HTTP %d: %s", response.status_code, response.text)
            raise
        except ValueError as e:
            logger.error("DWH-API: Ungueltige JSON-Response: %s", e)
            raise

    def get_gesamtstudierende(
        self,
        semester: str | None = None,
        hochschulzentrum: str | None = None,
        studiengang: str | None = None,
        ausrichtung: str | None = None,
        zeitmodell: str | None = None,
        kohorte: str | None = None,
        institut: str = "FOM",
        gruppierung: str | None = None,
    ) -> dict[str, Any]:
        """
        Ruft API-Endpoint '/gesamtstudierende' auf.

        Args:
            semester: z.B. '2026-WS' oder '2026-WS;2025-WS' fuer mehrere (ODER)
            hochschulzentrum: z.B. 'DLS'
            studiengang: z.B. 'Business Administration (BBA)'
            ausrichtung: z.B. 'Nationale Studienprogramme' (Standard-Wert)
            zeitmodell: z.B. 'Abendstudium'
            kohorte: z.B. '2026-WS'
            institut: z.B. 'FOM' (Standard)
            gruppierung: z.B. 'Semester;Hochschulzentrum' oder 'Semester,Hochschulzentrum'

        Returns:
            API-Response mit 'filter', 'gruppierung', 'werte' (Array):
            {
                "filter": {"Semester": "...", "Institut": "FOM", ...},
                "gruppierung": ["Semester"],
                "werte": [
                    {
                        "gruppen": "@{Semester=2026-WS}",
                        "Gesamtstudierende(mit_UV)": 44525,
                        "Gesamtstudierende(ohne_UV)": 43877
                    },
                    ...
                ]
            }
        """
        params = {"Institut": institut}

        if semester:
            params["Semester"] = semester
        if hochschulzentrum:
            params["Hochschulzentrum"] = hochschulzentrum
        if studiengang:
            params["Studiengang"] = studiengang
        if ausrichtung:
            params["Ausrichtung"] = ausrichtung
        if zeitmodell:
            params["Zeitmodell"] = zeitmodell
        if kohorte:
            params["Kohorte"] = kohorte
        if gruppierung:
            params["gruppierung"] = gruppierung

        return self._api_call("gesamtstudierende", params)

    def get_dimension_werte(self, dimension: str) -> dict[str, Any]:
        """
        Ruft API-Endpoint '/gesamtstudierende/dimensionen/{dimension}/werte' auf.

        Listet alle moeglichen Werte fuer eine Dimension auf.

        Args:
            dimension: z.B. 'Semester', 'Hochschulzentrum', 'Studiengang', 'Ausrichtung', etc.

        Returns:
            API-Response mit verfuegbaren Werten:
            {
                "dimension": "Semester",
                "werte": ["2026-WS", "2026-SS", "2025-WS", ...]
            }
        """
        return self._api_call(f"gesamtstudierende/dimensionen/{dimension}/werte")

    def close(self):
        """Schliesst die Session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> DWHAPIConnector:
        """Context Manager Support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager Support - schliesst Session."""
        self.close()


def create_connector_from_flask_config(app) -> DWHAPIConnector:
    """
    Erstellt DWHAPIConnector mit API-Key aus Flask app.config (Key Vault).

    Args:
        app: Flask-Application (muss 'DWH-API' in config haben)

    Returns:
        Initialisierter DWHAPIConnector

    Raises:
        ValueError: Falls API-Key nicht in config vorhanden
    """
    api_key = app.config.get("DWH_API_KEY")
    if not api_key:
        raise ValueError(
            "API-Key 'DWH-API' nicht in Config gefunden. "
            "Stelle sicher, dass 'DWH-API' in Azure Key Vault existiert."
        )
    return DWHAPIConnector(api_key=api_key)
