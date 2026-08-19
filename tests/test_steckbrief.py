"""Tests fuer services/steckbrief.py - Zuzahler Top-10-Logik."""

from unittest.mock import MagicMock, patch

import pytest

_SVC = "studiengang_steckbriefe.services.steckbrief"


# ===================================================================
# Hilfsfunktionen
# ===================================================================


def _make_cursor(rows, columns=("Firmenname", "Semesterkuerzel", "Anzahl")):
    """Erzeugt einen Mock-Cursor mit vordefinierten Ergebnissen."""
    cursor = MagicMock()
    cursor.description = [(col,) for col in columns]
    cursor.fetchall.return_value = rows
    return cursor


def _make_conn(cursor):
    """Erzeugt eine Mock-Connection, die den angegebenen Cursor liefert."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def _zuz_rows(sems=("2024-WS", "2025-SS")):
    return [{"Semesterkuerzel": s, "Total": 100, "Zuzahler": 20} for s in sems]


# ===================================================================
# _fetch_top10_firmen
# ===================================================================


class TestFetchTop10Firmen:
    @patch(f"{_SVC}.expand_pk", return_value=["WM"])
    @patch(f"{_SVC}.release_connection")
    @patch(f"{_SVC}.get_connection")
    def test_gibt_top10_zurueck(self, mock_get_conn, mock_release, mock_expand):
        """Happy-Path: Rohdaten werden korrekt zu {name, werte} aufbereitet."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        rows = [
            ("ACME GmbH", "2024-WS", 5),
            ("ACME GmbH", "2025-SS", 3),
            ("Firma B AG", "2024-WS", 2),
        ]
        mock_get_conn.return_value = _make_conn(_make_cursor(rows))

        result = _fetch_top10_firmen("WM", ["2024-WS", "2025-SS"])

        assert len(result) == 2
        acme = next(f for f in result if f["name"] == "ACME GmbH")
        assert acme["werte"] == [5, 3]
        firma_b = next(f for f in result if f["name"] == "Firma B AG")
        assert firma_b["werte"] == [2, None]

    @patch(f"{_SVC}.expand_pk", return_value=["WM"])
    @patch(f"{_SVC}.release_connection")
    @patch(f"{_SVC}.get_connection")
    def test_leere_rohdaten_gibt_leere_liste(self, mock_get_conn, mock_release, mock_expand):
        """Keine DB-Zeilen -> leere Top-10-Liste."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        mock_get_conn.return_value = _make_conn(_make_cursor([]))

        result = _fetch_top10_firmen("WM", ["2024-WS"])

        assert result == []

    @patch(f"{_SVC}.expand_pk", return_value=["WM"])
    @patch(f"{_SVC}.release_connection")
    @patch(f"{_SVC}.get_connection")
    def test_filtert_muell_firmennamen(self, mock_get_conn, mock_release, mock_expand):
        """Namen mit ',', 'z. Hd.' oder Laenge < 3 werden gefiltert."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        rows = [
            (",Irgendwas", "2024-WS", 10),
            ("z. Hd. Frau Muster", "2024-WS", 8),
            ("AB", "2024-WS", 5),
            ("OK GmbH", "2024-WS", 3),
        ]
        mock_get_conn.return_value = _make_conn(_make_cursor(rows))

        result = _fetch_top10_firmen("WM", ["2024-WS"])

        names = [f["name"] for f in result]
        assert "OK GmbH" in names
        assert not any(n.startswith(",") for n in names)
        assert not any(n.startswith("z. Hd.") for n in names)
        assert not any(len(n) < 3 for n in names)

    @patch(f"{_SVC}.expand_pk", return_value=["WM"])
    @patch(f"{_SVC}.release_connection")
    @patch(f"{_SVC}.get_connection")
    def test_trimmt_auf_10_eintraege(self, mock_get_conn, mock_release, mock_expand):
        """Mehr als 10 gueltige Firmen werden auf 10 gekuerzt."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        rows = [(f"Firma {i:02d} GmbH", "2024-WS", 10 - i) for i in range(12)]
        mock_get_conn.return_value = _make_conn(_make_cursor(rows))

        result = _fetch_top10_firmen("WM", ["2024-WS"])

        assert len(result) == 10

    @patch(f"{_SVC}.expand_pk", return_value=["WM"])
    @patch(f"{_SVC}.release_connection")
    @patch(f"{_SVC}.get_connection")
    def test_connection_wird_immer_freigegeben(self, mock_get_conn, mock_release, mock_expand):
        """release_connection wird auch bei Exception aufgerufen."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        conn = MagicMock()
        conn.cursor.side_effect = RuntimeError("DB-Fehler")
        mock_get_conn.return_value = conn

        with pytest.raises(RuntimeError):
            _fetch_top10_firmen("WM", ["2024-WS"])

        mock_release.assert_called_once_with(conn)


# ===================================================================
# get_zuzahler
# ===================================================================


class TestGetZuzahler:
    @patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"]))
    @patch(f"{_SVC}._fetch_top10_firmen", return_value=[{"name": "ACME", "werte": [5, 3]}])
    @patch(f"{_SVC}.query_db")
    @patch(f"{_SVC}.cache_set")
    @patch(f"{_SVC}.cache_get", return_value=None)
    def test_gibt_erwartete_struktur_zurueck(
        self, mock_get, mock_set, mock_db, mock_top10, mock_expand
    ):
        """get_zuzahler liefert alle Pflichtfelder im Ergebnis-Dict."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        mock_db.return_value = _zuz_rows()

        result = get_zuzahler("WM")

        assert "semester" in result
        assert "absolut" in result
        assert "pct_sg" in result
        assert "pct_fom" in result
        assert "top10" in result
        assert "gesamtergebnis" in result

    @patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"]))
    @patch(f"{_SVC}._fetch_top10_firmen")
    @patch(f"{_SVC}.query_db")
    @patch(f"{_SVC}.cache_set")
    @patch(f"{_SVC}.cache_get", return_value=None)
    def test_top10_wird_befuellt(self, mock_get, mock_set, mock_db, mock_top10, mock_expand):
        """top10 im Ergebnis ist nicht leer, wenn _fetch_top10_firmen Daten liefert."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        mock_db.return_value = _zuz_rows()
        expected_top10 = [{"name": "ACME GmbH", "werte": [5, 3]}]
        mock_top10.return_value = expected_top10

        result = get_zuzahler("WM")

        assert result["top10"] == expected_top10

    @patch(f"{_SVC}.query_db")
    @patch(f"{_SVC}.cache_get")
    def test_cache_hit_gibt_gecachten_wert_zurueck(self, mock_get, mock_db):
        """Bei Cache-Treffer werden keine DB-Aufrufe gemacht."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        cached = {"semester": ["WS-2024"], "absolut": [10], "top10": []}
        mock_get.return_value = cached

        result = get_zuzahler("WM")

        assert result == cached
        mock_db.assert_not_called()

    @patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"]))
    @patch(f"{_SVC}._fetch_top10_firmen", return_value=[])
    @patch(f"{_SVC}.query_db")
    @patch(f"{_SVC}.cache_set")
    @patch(f"{_SVC}.cache_get", return_value=None)
    def test_pct_sg_berechnung(self, mock_get, mock_set, mock_db, mock_top10, mock_expand):
        """Prozentsatz wird korrekt berechnet (Zuzahler / Total * 100)."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        mock_db.return_value = [{"Semesterkuerzel": "2024-WS", "Total": 200, "Zuzahler": 50}]

        result = get_zuzahler("WM")

        assert result["pct_sg"] == [25.0]

    @patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"]))
    @patch(f"{_SVC}._fetch_top10_firmen", return_value=[])
    @patch(f"{_SVC}.query_db")
    @patch(f"{_SVC}.cache_set")
    @patch(f"{_SVC}.cache_get", return_value=None)
    def test_ergebnis_wird_gecacht(self, mock_get, mock_set, mock_db, mock_top10, mock_expand):
        """Das Ergebnis wird nach Berechnung in den Cache geschrieben."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        mock_db.return_value = _zuz_rows()

        get_zuzahler("WM")

        assert mock_set.called
        cache_keys = [c[0][0] for c in mock_set.call_args_list]
        assert any("zuzahler_WM" in k for k in cache_keys)
