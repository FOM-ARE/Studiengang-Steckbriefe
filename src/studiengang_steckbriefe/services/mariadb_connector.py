"""MariaDB-Connector fuer die Konfigurations-Datenbank (HochschulorgaApps)."""

import ssl

import pymysql
from flask import current_app


def get_connection():
    """Erstellt eine neue MariaDB-Verbindung aus der App-Konfiguration."""
    kwargs = {
        "host": current_app.config["MARIADB_HOST"],
        "port": current_app.config["MARIADB_PORT"],
        "user": current_app.config["MARIADB_USER"],
        "password": current_app.config["MARIADB_PASSWORD"],
        "database": current_app.config["MARIADB_DATABASE"],
        "charset": current_app.config["MARIADB_CHARSET"],
    }

    if current_app.config.get("MARIADB_SSL"):
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl"] = ssl_ctx

    return pymysql.connect(**kwargs)


def query(sql: str, params=None) -> list[dict]:
    """Fuehrt ein SELECT aus und gibt eine Liste von Dicts zurueck."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            columns = [col[0] for col in cur.description]
            return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]
    finally:
        conn.close()


def execute(sql: str, params=None) -> int:
    """Fuehrt ein INSERT/UPDATE/DELETE aus und gibt affected rows zurueck."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()
