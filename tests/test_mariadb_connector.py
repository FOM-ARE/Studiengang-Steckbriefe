"""Tests fuer services/mariadb_connector.py."""

from unittest.mock import MagicMock, patch

_MODULE = "studiengang_steckbriefe.services.mariadb_connector"


class TestGetConnection:
    def test_ohne_ssl(self, app):
        with app.app_context():
            app.config["MARIADB_SSL"] = False
            mock_conn = MagicMock()
            with patch(f"{_MODULE}.pymysql.connect", return_value=mock_conn) as mock_connect:
                from studiengang_steckbriefe.services import mariadb_connector

                conn = mariadb_connector.get_connection()
        assert conn is mock_conn
        call_kwargs = mock_connect.call_args.kwargs
        assert "ssl" not in call_kwargs

    def test_mit_ssl_ohne_ca(self, app):
        with app.app_context():
            app.config["MARIADB_SSL"] = True
            app.config["MARIADB_SSL_CA"] = ""
            mock_conn = MagicMock()
            with patch(f"{_MODULE}.pymysql.connect", return_value=mock_conn):
                with patch(f"{_MODULE}.ssl.create_default_context") as mock_ssl:
                    from studiengang_steckbriefe.services import mariadb_connector

                    mariadb_connector.get_connection()
        mock_ssl.assert_called_once_with()

    def test_mit_ssl_und_ca(self, app):
        with app.app_context():
            app.config["MARIADB_SSL"] = True
            app.config["MARIADB_SSL_CA"] = "/etc/ssl/ca.crt"
            mock_conn = MagicMock()
            with patch(f"{_MODULE}.pymysql.connect", return_value=mock_conn):
                with patch(f"{_MODULE}.ssl.create_default_context") as mock_ssl:
                    from studiengang_steckbriefe.services import mariadb_connector

                    mariadb_connector.get_connection()
        mock_ssl.assert_called_once_with(cafile="/etc/ssl/ca.crt")


class TestQuery:
    def _make_mock_conn(self, description, rows):
        mock_cursor = MagicMock()
        mock_cursor.description = description
        mock_cursor.fetchall.return_value = rows
        # Context-Manager: __enter__ muss mock_cursor zurueckgeben
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_gibt_liste_von_dicts_zurueck(self, app):
        mock_conn, _ = self._make_mock_conn([("id",), ("name",)], [(1, "Test"), (2, "Demo")])
        from studiengang_steckbriefe.services import mariadb_connector

        with patch.object(mariadb_connector, "get_connection", return_value=mock_conn):
            result = mariadb_connector.query("SELECT id, name FROM t")
        assert result == [{"id": 1, "name": "Test"}, {"id": 2, "name": "Demo"}]
        mock_conn.close.assert_called_once()

    def test_mit_params(self, app):
        mock_conn, mock_cursor = self._make_mock_conn([("id",)], [(42,)])
        from studiengang_steckbriefe.services import mariadb_connector

        with patch.object(mariadb_connector, "get_connection", return_value=mock_conn):
            result = mariadb_connector.query("SELECT id FROM t WHERE id = %s", (42,))
        mock_cursor.execute.assert_called_once_with("SELECT id FROM t WHERE id = %s", (42,))
        assert result == [{"id": 42}]

    def test_ohne_params(self, app):
        mock_conn, mock_cursor = self._make_mock_conn([("x",)], [(7,)])
        from studiengang_steckbriefe.services import mariadb_connector

        with patch.object(mariadb_connector, "get_connection", return_value=mock_conn):
            mariadb_connector.query("SELECT x FROM t")
        mock_cursor.execute.assert_called_once_with("SELECT x FROM t")


class TestExecute:
    def _make_mock_conn(self, rowcount=1):
        mock_cursor = MagicMock()
        mock_cursor.rowcount = rowcount
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_gibt_rowcount_zurueck(self, app):
        mock_conn, _ = self._make_mock_conn(rowcount=3)
        from studiengang_steckbriefe.services import mariadb_connector

        with patch.object(mariadb_connector, "get_connection", return_value=mock_conn):
            count = mariadb_connector.execute("UPDATE t SET x = 1", (1,))
        assert count == 3
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_ohne_params(self, app):
        mock_conn, mock_cursor = self._make_mock_conn(rowcount=2)
        from studiengang_steckbriefe.services import mariadb_connector

        with patch.object(mariadb_connector, "get_connection", return_value=mock_conn):
            count = mariadb_connector.execute("DELETE FROM t WHERE id = 1")
        mock_cursor.execute.assert_called_once_with("DELETE FROM t WHERE id = 1")
        assert count == 2
