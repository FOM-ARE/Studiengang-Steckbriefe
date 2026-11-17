"""Tests fuer DWH-API Connector."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from studiengang_steckbriefe.services.dwh_api_connector import (
    DWHAPIConnector,
    create_connector_from_flask_config,
)


@pytest.fixture
def connector():
    """Erstellt einen Test-Connector mit Dummy-Key."""
    return DWHAPIConnector(api_key="test_key_12345")


@pytest.fixture
def mock_response():
    """Mock-Response der API."""
    return {
        "filter": {
            "Semester": "2026-WS",
            "Ausrichtung": "Nationale Studienprogramme",
            "Institut": "FOM",
        },
        "gruppierung": ["Semester"],
        "werte": [
            {
                "gruppen": "@{Semester=2026-WS}",
                "Gesamtstudierende(mit_UV)": 44525,
                "Gesamtstudierende(ohne_UV)": 43877,
            }
        ],
    }


class TestDWHAPIConnector:
    """Tests fuer DWHAPIConnector Klasse."""

    def test_init_with_api_key(self):
        """Test: Connector wird mit API-Key initialisiert."""
        api_key = "test_key_xyz"
        connector = DWHAPIConnector(api_key=api_key)
        assert connector.api_key == api_key

    def test_init_without_api_key(self):
        """Test: Connector kann ohne API-Key initialisiert werden."""
        connector = DWHAPIConnector()
        assert connector.api_key is None

    @patch("requests.Session.get")
    def test_get_gesamtstudierende_success(self, mock_get, connector, mock_response):
        """Test: Erfolgreiche API-Abfrage."""
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = connector.get_gesamtstudierende(semester="2026-WS", gruppierung="Semester")

        assert result == mock_response
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_get_gesamtstudierende_with_params(self, mock_get, connector):
        """Test: Parameter werden korrekt uebergeben."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"werte": []}
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        connector.get_gesamtstudierende(
            semester="2026-WS",
            hochschulzentrum="DLS",
            studiengang="Business Administration (BBA)",
        )

        # Pruefen, dass Parameters korrekt uebergeben wurden
        call_args = mock_get.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["Semester"] == "2026-WS"
        assert params["Hochschulzentrum"] == "DLS"
        assert params["Studiengang"] == "Business Administration (BBA)"
        assert params["Institut"] == "FOM"

    @patch("requests.Session.get")
    def test_get_gesamtstudierende_401_unauthorized(self, mock_get, connector):
        """Test: Fehlerbehandlung bei 401 Unauthorized."""
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            connector.get_gesamtstudierende()

    @patch("requests.Session.get")
    def test_get_gesamtstudierende_timeout(self, mock_get, connector):
        """Test: Fehlerbehandlung bei Timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout nach 15s")

        with pytest.raises(requests.exceptions.Timeout):
            connector.get_gesamtstudierende()

    @patch("requests.Session.get")
    def test_get_dimension_werte(self, mock_get, connector):
        """Test: Dimension-Werte abrufen."""
        mock_response = {
            "dimension": "Semester",
            "werte": ["2026-WS", "2026-SS", "2025-WS"],
        }
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = connector.get_dimension_werte("Semester")

        assert result == mock_response
        call_args = mock_get.call_args
        assert "gesamtstudierende/dimensionen/Semester/werte" in call_args[0][0]

    def test_context_manager(self, connector):
        """Test: Connector als Context Manager."""
        with connector as ctx:
            assert ctx is connector
        # Session sollte nach __exit__ None sein
        assert connector._session is None

    @patch("requests.Session.get")
    def test_api_key_in_header(self, mock_get, connector, mock_response):
        """Test: API-Key wird in X-API-Key Header uebergeben."""
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        connector.get_gesamtstudierende()

        # Pruefen, dass Header gesetzt wurden
        session = connector._get_session()
        assert session.headers.get("X-API-Key") == "test_key_12345"


class TestCreateConnectorFromFlaskConfig:
    """Tests fuer create_connector_from_flask_config()."""

    def test_create_with_valid_key(self):
        """Test: Connector wird mit gueltigem Key aus Config erstellt."""
        mock_app = MagicMock()
        mock_app.config = {"DWH_API_KEY": "my_secret_key"}

        connector = create_connector_from_flask_config(mock_app)

        assert connector.api_key == "my_secret_key"

    def test_create_without_key_raises_error(self):
        """Test: ValueError wird geworfen, wenn Key fehlt."""
        mock_app = MagicMock()
        mock_app.config = {}

        with pytest.raises(ValueError, match="DWH-API.*Key Vault"):
            create_connector_from_flask_config(mock_app)


class TestAPIErrorHandling:
    """Tests fuer Fehlerbehandlung."""

    @patch("requests.Session.get")
    def test_connection_error(self, mock_get, connector):
        """Test: ConnectionError wird weitergeleitet."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            connector.get_gesamtstudierende()

    @patch("requests.Session.get")
    def test_invalid_json_response(self, mock_get, connector):
        """Test: ValueError bei ungueltigem JSON."""
        mock_resp = Mock()
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError):
            connector.get_gesamtstudierende()

    @patch("requests.Session.get")
    def test_http_400_bad_request(self, mock_get, connector):
        """Test: HTTP 400 wird korrekt behandelt."""
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.text = "Invalid grouping dimension"
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            connector.get_gesamtstudierende(gruppierung="InvalidDimension")

    @patch("requests.Session.get")
    def test_http_300_maintenance(self, mock_get, connector):
        """Test: HTTP 300 (Wartungsfenster) wird erkannt."""
        mock_resp = Mock()
        mock_resp.status_code = 300
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("300")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            connector.get_gesamtstudierende()


class TestParameterHandling:
    """Tests fuer Parameter-Behandlung."""

    @patch("requests.Session.get")
    def test_multiple_semesters_or_logic(self, mock_get, connector):
        """Test: Mehrere Semester mit Semikolon (ODER-Logik)."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"werte": []}
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        connector.get_gesamtstudierende(semester="2026-WS;2025-WS")

        params = mock_get.call_args.kwargs["params"]
        assert params["Semester"] == "2026-WS;2025-WS"

    @patch("requests.Session.get")
    def test_gruppierung_multiple_dimensions(self, mock_get, connector):
        """Test: Mehrere Dimensionen fuer Gruppierung."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"werte": []}
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        connector.get_gesamtstudierende(gruppierung="Semester;Hochschulzentrum")

        params = mock_get.call_args.kwargs["params"]
        assert params["gruppierung"] == "Semester;Hochschulzentrum"

    @patch("requests.Session.get")
    def test_optional_params_not_included_if_none(self, mock_get, connector):
        """Test: Optionale Parameter werden nicht uebergeben, wenn None."""
        mock_resp = Mock()
        mock_resp.json.return_value = {"werte": []}
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        connector.get_gesamtstudierende(semester="2026-WS")

        params = mock_get.call_args.kwargs["params"]
        assert "Hochschulzentrum" not in params
        assert "Studiengang" not in params
        assert "Zeitmodell" not in params
