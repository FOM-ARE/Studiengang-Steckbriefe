"""Tests fuer services/steckbrief.py – Zuzahler Top-10-Logik."""

from unittest.mock import MagicMock, patch

import pytest

_SVC = "studiengang_steckbriefe.services.steckbrief"


# ===================================================================
# _fetch_top10_firmen
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


class TestFetchTop10Firmen:
    def test_gibt_top10_zurueck(self):
        """Happy-Path: Rohdaten werden korrekt zu {name, werte} aufbereitet."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        rows = [
            ("ACME GmbH", "2024-WS", 5),
            ("ACME GmbH", "2025-SS", 3),
            ("Firma B AG", "2024-WS", 2),
        ]
        cursor = _make_cursor(rows)
        conn = _make_conn(cursor)

        with (
            patch(f"{_SVC}.get_connection", return_value=conn),
            patch(f"{_SVC}.release_connection"),
            patch(f"{_SVC}.expand_pk", return_value=["WM"]),
        ):
            result = _fetch_top10_firmen("WM", ["2024-WS", "2025-SS"])

        assert len(result) == 2
        acme = next(f for f in result if f["name"] == "ACME GmbH")
        assert acme["werte"] == [5, 3]
        firma_b = next(f for f in result if f["name"] == "Firma B AG")
        assert firma_b["werte"] == [2, None]

    def test_leere_rohdaten_gibt_leere_liste(self):
        """Keine DB-Zeilen -> leere Top-10-Liste."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        cursor = _make_cursor([])
        conn = _make_conn(cursor)

        with (
            patch(f"{_SVC}.get_connection", return_value=conn),
            patch(f"{_SVC}.release_connection"),
            patch(f"{_SVC}.expand_pk", return_value=["WM"]),
        ):
            result = _fetch_top10_firmen("WM", ["2024-WS"])

        assert result == []

    def test_filtert_muell_firmennamen(self):
        """Namen mit ',', 'z. Hd.' oder Laenge < 3 werden gefiltert."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        rows = [
            (",Irgendwas", "2024-WS", 10),
            ("z. Hd. Frau Muster", "2024-WS", 8),
            ("AB", "2024-WS", 5),
            ("OK GmbH", "2024-WS", 3),
        ]
        cursor = _make_cursor(rows)
        conn = _make_conn(cursor)

        with (
            patch(f"{_SVC}.get_connection", return_value=conn),
            patch(f"{_SVC}.release_connection"),
            patch(f"{_SVC}.expand_pk", return_value=["WM"]),
        ):
            result = _fetch_top10_firmen("WM", ["2024-WS"])

        names = [f["name"] for f in result]
        assert "OK GmbH" in names
        assert not any(n.startswith(",") for n in names)
        assert not any(n.startswith("z. Hd.") for n in names)
        assert not any(len(n) < 3 for n in names)

    def test_trimmt_auf_10_eintraege(self):
        """Mehr als 10 gueltige Firmen werden auf 10 gekuerzt."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        rows = [(f"Firma {i:02d} GmbH", "2024-WS", 10 - i) for i in range(12)]
        cursor = _make_cursor(rows)
        conn = _make_conn(cursor)

        with (
            patch(f"{_SVC}.get_connection", return_value=conn),
            patch(f"{_SVC}.release_connection"),
            patch(f"{_SVC}.expand_pk", return_value=["WM"]),
        ):
            result = _fetch_top10_firmen("WM", ["2024-WS"])

        assert len(result) == 10

    def test_connection_wird_immer_freigegeben(self):
        """release_connection wird auch bei Exception aufgerufen."""
        from studiengang_steckbriefe.services.steckbrief import _fetch_top10_firmen

        conn = MagicMock()
        conn.cursor.side_effect = RuntimeError("DB-Fehler")

        with (
            patch(f"{_SVC}.get_connection", return_value=conn),
            patch(f"{_SVC}.release_connection") as mock_release,
            patch(f"{_SVC}.expand_pk", return_value=["WM"]),
        ):
            with pytest.raises(RuntimeError):
                _fetch_top10_firmen("WM", ["2024-WS"])

        mock_release.assert_called_once_with(conn)


# ===================================================================
# get_zuzahler
# ===================================================================


class TestGetZuzahler:
    def _zuz_rows(self, sems=("2024-WS", "2025-SS")):
        return [{"Semesterkuerzel": s, "Total": 100, "Zuzahler": 20} for s in sems]

    def test_gibt_erwartete_struktur_zurueck(self):
        """get_zuzahler liefert alle Pflichtfelder im Ergebnis-Dict."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        zuz_rows = self._zuz_rows()
        with (
            patch(f"{_SVC}.cache_get", return_value=None),
            patch(f"{_SVC}.cache_set"),
            patch(f"{_SVC}.query_db", return_value=zuz_rows),
            patch(f"{_SVC}._fetch_top10_firmen", return_value=[{"name": "ACME", "werte": [5, 3]}]),
            patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"])),
        ):
            result = get_zuzahler("WM")

        assert "semester" in result
        assert "absolut" in result
        assert "pct_sg" in result
        assert "pct_fom" in result
        assert "top10" in result
        assert "gesamtergebnis" in result

    def test_top10_wird_befuellt(self):
        """top10 im Ergebnis ist nicht mehr leer, wenn _fetch_top10_firmen Daten liefert."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        zuz_rows = self._zuz_rows()
        expected_top10 = [{"name": "ACME GmbH", "werte": [5, 3]}]

        with (
            patch(f"{_SVC}.cache_get", return_value=None),
            patch(f"{_SVC}.cache_set"),
            patch(f"{_SVC}.query_db", return_value=zuz_rows),
            patch(f"{_SVC}._fetch_top10_firmen", return_value=expected_top10),
            patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"])),
        ):
            result = get_zuzahler("WM")

        assert result["top10"] == expected_top10

    def test_cache_hit_gibt_gecachten_wert_zurueck(self):
        """Bei Cache-Treffer werden keine DB-Aufrufe gemacht."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        cached = {"semester": ["WS-2024"], "absolut": [10], "top10": []}

        with (
            patch(f"{_SVC}.cache_get", return_value=cached),
            patch(f"{_SVC}.query_db") as mock_db,
        ):
            result = get_zuzahler("WM")

        assert result == cached
        mock_db.assert_not_called()

    def test_pct_sg_berechnung(self):
        """Prozentsatz wird korrekt berechnet (Zuzahler / Total * 100)."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        zuz_rows = [{"Semesterkuerzel": "2024-WS", "Total": 200, "Zuzahler": 50}]

        with (
            patch(f"{_SVC}.cache_get", return_value=None),
            patch(f"{_SVC}.cache_set"),
            patch(f"{_SVC}.query_db", return_value=zuz_rows),
            patch(f"{_SVC}._fetch_top10_firmen", return_value=[]),
            patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"])),
        ):
            result = get_zuzahler("WM")

        assert result["pct_sg"] == [25.0]

    def test_ergebnis_wird_gecacht(self):
        """Das Ergebnis wird nach Berechnung in den Cache geschrieben."""
        from studiengang_steckbriefe.services.steckbrief import get_zuzahler

        zuz_rows = self._zuz_rows()

        with (
            patch(f"{_SVC}.cache_get", return_value=None),
            patch(f"{_SVC}.cache_set") as mock_set,
            patch(f"{_SVC}.query_db", return_value=zuz_rows),
            patch(f"{_SVC}._fetch_top10_firmen", return_value=[]),
            patch(f"{_SVC}.pk_expand_sql", return_value=("SQL", ["WM"])),
        ):
            get_zuzahler("WM")

        assert mock_set.called
        cache_keys = [c[0][0] for c in mock_set.call_args_list]
        assert any("zuzahler_WM" in k for k in cache_keys)
