"""Tests fuer services/db_connector.py."""

import queue
from unittest.mock import MagicMock, patch

import pytest

_MODULE = "studiengang_steckbriefe.services.db_connector"


class TestBuildConnectionString:
    def test_expliziter_connection_string_hat_vorrang(self, app):
        with app.app_context():
            app.config["DWH_CONNECTION_STRING"] = "Server=explicit;Database=test"
            from studiengang_steckbriefe.services import db_connector

            result = db_connector._build_connection_string()
        assert result == "Server=explicit;Database=test"
        app.config.pop("DWH_CONNECTION_STRING", None)

    def test_sql_auth_connection_string(self, app):
        with app.app_context():
            app.config.pop("DWH_CONNECTION_STRING", None)
            app.config["DWH_AUTHENTICATION"] = "SQL"
            app.config["DWH_HOST"] = "sql-server"
            app.config["DWH_PORT"] = "1433"
            app.config["DWH_DATABASE"] = "BCW_DWH"
            app.config["DWH_USER"] = "sa"
            app.config["DWH_PASSWORD"] = "secret"
            with patch(f"{_MODULE}.pyodbc.drivers", return_value=[]):
                from studiengang_steckbriefe.services import db_connector

                result = db_connector._build_connection_string()
        assert "UID=sa" in result
        assert "PWD=secret" in result
        assert "SERVER=sql-server,1433" in result

    def test_windows_auth_connection_string(self, app):
        with app.app_context():
            app.config.pop("DWH_CONNECTION_STRING", None)
            app.config["DWH_AUTHENTICATION"] = "Windows"
            app.config["DWH_HOST"] = "sql-server"
            app.config["DWH_PORT"] = "1433"
            app.config["DWH_DATABASE"] = "BCW_DWH"
            with patch(f"{_MODULE}.pyodbc.drivers", return_value=[]):
                from studiengang_steckbriefe.services import db_connector

                result = db_connector._build_connection_string()
        assert "Trusted_Connection=yes" in result
        assert "UID" not in result

    def test_nutzt_neuesten_treiber(self, app):
        with app.app_context():
            app.config.pop("DWH_CONNECTION_STRING", None)
            app.config["DWH_AUTHENTICATION"] = "SQL"
            app.config["DWH_HOST"] = "h"
            app.config["DWH_PORT"] = "1433"
            app.config["DWH_DATABASE"] = "db"
            app.config["DWH_USER"] = "u"
            app.config["DWH_PASSWORD"] = "p"
            drivers = ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server"]
            with patch(f"{_MODULE}.pyodbc.drivers", return_value=drivers):
                from studiengang_steckbriefe.services import db_connector

                result = db_connector._build_connection_string()
        assert "ODBC Driver 18 for SQL Server" in result


class TestInitPool:
    def test_setzt_conn_str(self, app):
        from studiengang_steckbriefe.services import db_connector

        with patch.object(db_connector, "_build_connection_string", return_value="DRIVER=test;"):
            db_connector.init_pool(app)
        assert db_connector._CONN_STR == "DRIVER=test;"


class TestGetConnection:
    def _leere_pool(self):
        from studiengang_steckbriefe.services import db_connector

        while not db_connector._CONN_POOL.empty():
            try:
                db_connector._CONN_POOL.get_nowait()
            except queue.Empty:
                break

    def test_neue_verbindung_wenn_pool_leer(self, app):
        from studiengang_steckbriefe.services import db_connector

        self._leere_pool()
        db_connector._CONN_STR = "DRIVER=mock;"
        mock_conn = MagicMock()
        with patch(f"{_MODULE}.pyodbc.connect", return_value=mock_conn) as mock_connect:
            conn = db_connector.get_connection()
        mock_connect.assert_called_once_with("DRIVER=mock;", timeout=30)
        assert conn is mock_conn

    def test_verbindung_aus_pool(self, app):
        from studiengang_steckbriefe.services import db_connector

        self._leere_pool()
        mock_conn = MagicMock()
        mock_conn.execute.return_value = None
        db_connector._CONN_POOL.put_nowait(mock_conn)
        conn = db_connector.get_connection()
        assert conn is mock_conn

    def test_defekte_pool_verbindung_ersetzt_durch_neue(self, app):
        from studiengang_steckbriefe.services import db_connector

        self._leere_pool()
        bad_conn = MagicMock()
        bad_conn.execute.side_effect = Exception("Verbindung tot")
        db_connector._CONN_POOL.put_nowait(bad_conn)
        db_connector._CONN_STR = "DRIVER=mock;"
        new_conn = MagicMock()
        with patch(f"{_MODULE}.pyodbc.connect", return_value=new_conn):
            conn = db_connector.get_connection()
        assert conn is new_conn


class TestReleaseConnection:
    def _leere_pool(self):
        from studiengang_steckbriefe.services import db_connector

        while not db_connector._CONN_POOL.empty():
            try:
                db_connector._CONN_POOL.get_nowait()
            except queue.Empty:
                break

    def test_gibt_verbindung_in_pool(self, app):
        from studiengang_steckbriefe.services import db_connector

        self._leere_pool()
        mock_conn = MagicMock()
        db_connector.release_connection(mock_conn)
        assert not db_connector._CONN_POOL.empty()

    def test_schliesst_verbindung_bei_vollem_pool(self, app):
        from studiengang_steckbriefe.services import db_connector

        self._leere_pool()
        while not db_connector._CONN_POOL.full():
            db_connector._CONN_POOL.put_nowait(MagicMock())
        extra = MagicMock()
        db_connector.release_connection(extra)
        extra.close.assert_called_once()


class TestQueryDb:
    def test_gibt_liste_von_dicts_zurueck(self, app):
        from studiengang_steckbriefe.services import db_connector

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "Alpha"), (2, "Beta")]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with patch.object(db_connector, "release_connection") as mock_release:
                result = db_connector.query_db("SELECT id, name FROM test")

        assert result == [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]
        mock_release.assert_called_once_with(mock_conn)

    def test_mit_params(self, app):
        from studiengang_steckbriefe.services import db_connector

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = [(42,)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with patch.object(db_connector, "release_connection"):
                result = db_connector.query_db("SELECT id FROM t WHERE id = ?", (42,))

        mock_cursor.execute.assert_called_once_with("SELECT id FROM t WHERE id = ?", (42,))
        assert result == [{"id": 42}]

    def test_exception_schliesst_verbindung_und_wirft(self, app):
        from studiengang_steckbriefe.services import db_connector

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Cursor-Fehler")

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with pytest.raises(Exception, match="Cursor-Fehler"):
                db_connector.query_db("SELECT 1")

        mock_conn.close.assert_called_once()

    def test_exception_close_wirft_ebenfalls(self, app):
        """Wenn close() beim Exception-Handling selbst wirft, wird das ignoriert."""
        from studiengang_steckbriefe.services import db_connector

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Cursor-Fehler")
        mock_conn.close.side_effect = Exception("Close-Fehler")

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with pytest.raises(Exception, match="Cursor-Fehler"):
                db_connector.query_db("SELECT 1")


class TestReleaseConnection:
    def test_close_bei_vollem_pool(self, app):
        """Wenn der Pool voll ist, wird die Verbindung geschlossen."""
        import queue
        from studiengang_steckbriefe.services import db_connector

        mock_conn = MagicMock()
        with patch.object(db_connector, "_CONN_POOL") as mock_pool:
            mock_pool.put_nowait.side_effect = queue.Full
            db_connector.release_connection(mock_conn)
        mock_conn.close.assert_called_once()

    def test_close_exception_bei_vollem_pool_wird_ignoriert(self, app):
        """Wenn close() beim Verwerfen wirft, bleibt kein Fehler."""
        import queue
        from studiengang_steckbriefe.services import db_connector

        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("Close-Fehler")
        with patch.object(db_connector, "_CONN_POOL") as mock_pool:
            mock_pool.put_nowait.side_effect = queue.Full
            db_connector.release_connection(mock_conn)  # darf nicht werfen


class TestQueryDbMulti:
    def test_fuehrt_mehrere_queries_aus(self, app):
        from studiengang_steckbriefe.services import db_connector

        mock_cursor = MagicMock()
        mock_cursor.description = [("x",)]
        mock_cursor.fetchall.side_effect = [[(1,)], [(2,)]]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with patch.object(db_connector, "release_connection"):
                result = db_connector.query_db_multi(
                    [
                        ("SELECT x FROM a", None),
                        ("SELECT x FROM b", (1,)),
                    ]
                )

        assert result == [[{"x": 1}], [{"x": 2}]]

    def test_exception_schliesst_verbindung(self, app):
        from studiengang_steckbriefe.services import db_connector

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Multi-Fehler")

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with pytest.raises(Exception, match="Multi-Fehler"):
                db_connector.query_db_multi([("SELECT 1", None)])

        mock_conn.close.assert_called_once()

    def test_exception_close_wirft_ebenfalls(self, app):
        """Wenn close() beim Exception-Handling in query_db_multi selbst wirft."""
        from studiengang_steckbriefe.services import db_connector

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Multi-Fehler")
        mock_conn.close.side_effect = Exception("Close-Fehler")

        with patch.object(db_connector, "get_connection", return_value=mock_conn):
            with pytest.raises(Exception, match="Multi-Fehler"):
                db_connector.query_db_multi([("SELECT 1", None)])
