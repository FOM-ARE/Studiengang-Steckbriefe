"""Tests fuer services/config_db.py."""

from unittest.mock import patch

_SAFE_QUERY = "studiengang_steckbriefe.services.config_db._safe_query"


def _empty(count):
    """Erstellt eine Liste von 'count' leeren Listen."""
    return [[] for _ in range(count)]


def _iter_results(results):
    """Gibt einen Side-Effect zurueck der Ergebnisse der Reihe nach liefert."""
    it = iter(results)
    return lambda _sql: next(it)


class TestSafeQuery:
    def test_fehler_gibt_leere_liste_zurueck(self, app):
        with app.app_context():
            with patch(
                "studiengang_steckbriefe.services.config_db.mariadb_connector.query",
                side_effect=Exception("DB nicht erreichbar"),
            ):
                from studiengang_steckbriefe.services import config_db

                result = config_db._safe_query("SELECT 1")
        assert result == []


class TestReloadConfig:
    def test_laedt_pk_mapping(self, app):
        results = [
            [{"AliasPk": "WM-DE", "BasisPk": "WM"}],
            [],
            [],
            [],
            [],
            [],
        ]
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(results)):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert config_db.PK_MAPPING == {"WM-DE": "WM"}
        assert "WM" in config_db.PK_REVERSE
        assert "WM-DE" in config_db.PK_REVERSE["WM"]

    def test_laedt_hsb_config_aus_db(self, app):
        hsb_row = {
            "HsbCode": "WB",
            "Name": "Wirtschaft",
            "Icon": "WB",
            "FarbeHex": "#003",
            "Sortierung": 1,
        }
        results = [
            [],
            [hsb_row],
            [],
            [],
            [],
            [],
        ]
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(results)):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert "WB" in config_db.HSB_CONFIG
        assert config_db.HSB_CONFIG["WB"]["hsb_name"] == "Wirtschaft"

    def test_fallback_wenn_hsb_config_leer(self, app):
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(_empty(6))):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert len(config_db.HSB_CONFIG) > 0

    def test_fallback_wenn_excluded_hsz_leer(self, app):
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(_empty(6))):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert len(config_db.EXCLUDED_HSZ) > 0

    def test_laedt_endpoint_params(self, app):
        results = [
            [],
            [],
            [],
            [],
            [{"EndpunktCode": "trends", "ParamName": "limit", "ParamWert": "12"}],
            [],
        ]
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(results)):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert config_db.ENDPOINT_PARAMS.get("trends", {}).get("limit") == "12"

    def test_laedt_anrechnung_regeln_und_offene_hochschule(self, app):
        results = [
            [],
            [],
            [],
            [
                {
                    "Regeltyp": "ANRECHNUNGSGRUND",
                    "AbgleichOperator": "=",
                    "AbgleichWert": "Meister",
                    "Kategorie": "OFFENE_HOCHSCHULE",
                    "Prioritaet": 1,
                }
            ],
            [],
            [],
        ]
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(results)):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert "ANRECHNUNGSGRUND" in config_db.ANRECHNUNG_REGELN
        assert "Meister" in config_db.OFFENE_HOCHSCHULE_GRUENDE

    def test_laedt_filterliste(self, app):
        results = [
            [],
            [],
            [],
            [],
            [],
            [{"Bereich": "UE_VERANSTTYP", "Wert": "Sonderveranstaltung", "Typ": "string"}],
        ]
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(results)):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert "Sonderveranstaltung" in config_db.FILTERLISTE.get("UE_VERANSTTYP", [])

    def test_fallback_wenn_filterliste_leer(self, app):
        with app.app_context():
            with patch(_SAFE_QUERY, side_effect=_iter_results(_empty(6))):
                from studiengang_steckbriefe.services import config_db

                config_db.reload_config()
        assert len(config_db.FILTERLISTE) > 0


class TestGetParam:
    def test_vorhanden(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {"ep": {"key": "wert"}}
        assert config_db.get_param("ep", "key") == "wert"

    def test_nicht_vorhanden_gibt_default(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {}
        assert config_db.get_param("x", "y", default="fallback") == "fallback"

    def test_nicht_vorhanden_gibt_none(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {}
        assert config_db.get_param("x", "y") is None


class TestGetParamInt:
    def test_konvertiert_zu_int(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {"ep": {"limit": "42"}}
        assert config_db.get_param_int("ep", "limit") == 42

    def test_fallback_bei_nicht_int(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {"ep": {"wert": "kein_int"}}
        assert config_db.get_param_int("ep", "wert", default=99) == 99

    def test_fallback_wenn_nicht_vorhanden(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {}
        assert config_db.get_param_int("ep", "x", default=5) == 5

    def test_fallback_bei_none(self):
        from studiengang_steckbriefe.services import config_db

        config_db.ENDPOINT_PARAMS = {"ep": {}}
        assert config_db.get_param_int("ep", "fehlt") == 0


class TestGetFilterValues:
    def test_gibt_werte_zurueck(self):
        from studiengang_steckbriefe.services import config_db

        config_db.FILTERLISTE = {"BEREICH": ["A", "B"]}
        assert config_db.get_filter_values("BEREICH") == ["A", "B"]

    def test_leer_fuer_unbekannten_bereich(self):
        from studiengang_steckbriefe.services import config_db

        config_db.FILTERLISTE = {}
        assert config_db.get_filter_values("UNBEKANNT") == []


class TestGetFilterSql:
    def test_gibt_sql_liste_zurueck(self):
        from studiengang_steckbriefe.services import config_db

        config_db.FILTERLISTE = {"BEREICH": ["Wert1", "Wert2"]}
        assert config_db.get_filter_sql("BEREICH") == "'Wert1','Wert2'"

    def test_sql_none_fuer_leere_liste(self):
        from studiengang_steckbriefe.services import config_db

        config_db.FILTERLISTE = {}
        assert config_db.get_filter_sql("LEER") == "'__NONE__'"
