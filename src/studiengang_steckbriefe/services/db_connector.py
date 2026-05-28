"""DWH-Datenbankzugriff via pyodbc mit Connection Pool."""

import queue
import threading

import pyodbc
from flask import current_app

_CONN_STR = None
_CONN_POOL = queue.Queue(maxsize=10)
_CONN_POOL_LOCK = threading.Lock()


def _build_connection_string() -> str:
    """Baut den Connection-String aus der App-Konfiguration."""
    # Falls ein vollstaendiger Connection String aus Key Vault vorliegt
    explicit = current_app.config.get("DWH_CONNECTION_STRING")
    if explicit:
        return explicit

    host = current_app.config["DWH_HOST"]
    port = current_app.config["DWH_PORT"]
    database = current_app.config["DWH_DATABASE"]
    auth = current_app.config["DWH_AUTHENTICATION"]

    driver = "{ODBC Driver 17 for SQL Server}"
    available = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if available:
        driver = "{" + available[-1] + "}"

    if auth == "Windows":
        return (
            f"DRIVER={driver};"
            f"SERVER={host},{port};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    else:
        user = current_app.config.get("DWH_USER", "")
        password = current_app.config.get("DWH_PASSWORD", "")
        return (
            f"DRIVER={driver};"
            f"SERVER={host},{port};"
            f"DATABASE={database};"
            f"UID={user};PWD={password};"
            f"TrustServerCertificate=yes;"
        )


def init_pool(app):
    """Initialisiert den Connection-String (einmalig beim App-Start)."""
    global _CONN_STR
    with app.app_context():
        _CONN_STR = _build_connection_string()


def get_connection():
    """Holt eine Verbindung aus dem Pool oder erstellt eine neue."""
    try:
        conn = _CONN_POOL.get_nowait()
        # Verbindung testen
        try:
            conn.execute("SELECT 1")
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
    except queue.Empty:
        pass

    return pyodbc.connect(_CONN_STR, timeout=30)


def release_connection(conn):
    """Gibt eine Verbindung zurueck in den Pool."""
    try:
        _CONN_POOL.put_nowait(conn)
    except queue.Full:
        try:
            conn.close()
        except Exception:
            pass


def query_db(sql: str, params=None) -> list[dict]:
    """Fuehrt ein SELECT aus und gibt eine Liste von Dicts zurueck."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
        release_connection(conn)
        return rows
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise


def query_db_multi(queries: list[tuple]) -> list[list[dict]]:
    """Fuehrt mehrere Queries auf EINER Connection aus.

    Args:
        queries: Liste von (sql, params) Tupeln.

    Returns:
        Liste von Ergebnis-Listen (eine pro Query).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        results = []
        for sql, params in queries:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            results.append(
                [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
            )
        release_connection(conn)
        return results
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
