"""
Steckbrief-Backend: Python/Flask + pyodbc → SQL Server DWH
Startet auf Port 5000, liefert Studierendenzahlen aus BCW_DWH.dwh.C_Studierendenzahlen
"""
import os
import time
import atexit
import pyodbc
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from functools import wraps
import ldap3
import config_db

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['http://localhost:8000', 'http://127.0.0.1:8000'])
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(32))
from datetime import timedelta
app.permanent_session_lifetime = timedelta(hours=8)

# ─── LDAP-Konfiguration ───
LDAP_SERVER = 'ldap://bcw-intern.local'
LDAP_DOMAIN = 'bcw-intern.local'
LDAP_BASE_DN = 'DC=bcw-intern,DC=local'

# ─── App-Berechtigungen (MariaDB: HochschulorgaApps.t_app_berechtigungen) ───
import json
import ssl as _ssl
import pymysql

APP_NAME = 'Studiengang-Steckbriefe'

DB_CONFIG_APPS = {
    'host': os.getenv('DB_HOST', 'mariadb.bcw-intern.local'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': 'HochschulorgaApps',
    'password': '%z8J9xjZha)9,)Jn',
    'database': 'HochschulorgaApps',
    'charset': 'utf8mb4',
}


def _get_apps_connection():
    """Erstellt eine MariaDB-Verbindung zur Berechtigungs-DB."""
    ssl_ctx = _ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = _ssl.CERT_NONE
    return pymysql.connect(**DB_CONFIG_APPS, ssl=ssl_ctx)


def _load_app_permissions():
    """Lädt Berechtigungen für diese App aus der DB.
    Gibt dict zurück: {recht: [{'berechtigt': ..., 'typ': ...}, ...]}"""
    conn = _get_apps_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT Berechtigt, Recht, Typ FROM t_app_berechtigungen "
                "WHERE App = %s AND Aktiv = 1",
                (APP_NAME,)
            )
            rows = cur.fetchall()
        result = {}
        for berechtigt, recht, typ in rows:
            result.setdefault(recht, []).append({
                'berechtigt': berechtigt.lower(),
                'typ': typ
            })
        return result
    finally:
        conn.close()


def _get_user_groups_from_ldap(conn):
    """Extrahiert die Gruppennamen (CN, lowercase) aus memberOf."""
    if not conn.entries:
        return []
    entry = conn.entries[0]
    member_of = entry.memberOf if hasattr(entry, 'memberOf') and entry.memberOf else []
    groups = []
    for dn in member_of:
        dn_str = str(dn)
        # CN= extrahieren
        for part in dn_str.split(','):
            if part.strip().upper().startswith('CN='):
                groups.append(part.strip()[3:].lower())
                break
    return groups


def _check_user_permission(username, user_groups, permissions, recht):
    """Prüft ob ein User ein bestimmtes Recht hat."""
    entries = permissions.get(recht, [])
    for entry in entries:
        if entry['typ'] == 'user' and entry['berechtigt'] == username.lower():
            return True
        if entry['typ'] == 'gruppe' and entry['berechtigt'] in user_groups:
            return True
    return False


def _determine_role(username, user_groups, permissions):
    """Bestimmt die höchste Rolle eines Users (admin > write > read)."""
    if _check_user_permission(username, user_groups, permissions, 'admin'):
        return 'admin'
    if _check_user_permission(username, user_groups, permissions, 'write'):
        return 'write'
    if _check_user_permission(username, user_groups, permissions, 'read'):
        return 'read'
    return None


def _auto_display_name(username):
    """Erzeugt Anzeigename aus vorname.nachname → Vorname Nachname."""
    name = username.split('@')[0] if '@' in username else username
    parts = name.split('.')
    return ' '.join(p.capitalize() for p in parts)


def authenticate_user(username, password):
    """LDAP-Bind + DB-Berechtigungsprüfung.
    Gibt dict mit Anzeigename, E-Mail und Rolle zurück oder None bei Fehler."""
    # 1) LDAP-Bind
    user_dn = f'{username}@{LDAP_DOMAIN}'
    server = ldap3.Server(LDAP_SERVER, get_info=ldap3.DSA)
    ldap_conn = ldap3.Connection(server, user=user_dn, password=password, authentication=ldap3.SIMPLE)
    try:
        if not ldap_conn.bind():
            return None

        # Benutzer im AD suchen – Anzeigename, E-Mail, Gruppen holen
        search_filter = f'(&(objectClass=user)(sAMAccountName={ldap3.utils.conv.escape_filter_chars(username)}))'
        ldap_conn.search(
            LDAP_BASE_DN,
            search_filter,
            attributes=['displayName', 'mail', 'memberOf']
        )

        if ldap_conn.entries:
            entry = ldap_conn.entries[0]
            display_name = str(entry.displayName) if entry.displayName else None
            email = str(entry.mail) if entry.mail else ''
        else:
            display_name = None
            email = ''

        if not display_name:
            display_name = _auto_display_name(username)

        # 2) Gruppen aus AD holen
        user_groups = _get_user_groups_from_ldap(ldap_conn)

        # 3) Berechtigungen aus DB laden und Rolle bestimmen
        permissions = _load_app_permissions()
        role = _determine_role(username, user_groups, permissions)

        if not role:
            return None  # Keine Berechtigung für diese App

        return {
            'username': username,
            'displayName': display_name,
            'email': email,
            'role': role
        }
    finally:
        ldap_conn.unbind()


def login_required(f):
    """Decorator: prüft ob Benutzer eingeloggt ist."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Nicht authentifiziert'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator: prüft ob Benutzer eingeloggt ist UND Admin-Rolle hat."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Nicht authentifiziert'}), 401
        if session['user'].get('role') != 'admin':
            return jsonify({'error': 'Keine Berechtigung (Admin erforderlich)'}), 403
        return f(*args, **kwargs)
    return decorated

# ─── Cache ───
CACHE = {}
def cache_get(key):
    """Gibt gecachten Wert zurück oder None wenn nicht vorhanden."""
    entry = CACHE.get(key)
    if entry:
        return entry['data']
    return None

def cache_set(key, data):
    """Speichert Daten im Cache mit Timestamp."""
    CACHE[key] = {'data': data, 'ts': time.time()}

# ─── Datenbank-Konfiguration ───
DWH_HOST = os.getenv('DWH_HOST', 'ms-sql-107.bcw-intern.local')
DWH_PORT = os.getenv('DWH_PORT', '1433')
DWH_DATABASE = os.getenv('DWH_DATABASE', 'BCW_DWH')
DWH_AUTHENTICATION = os.getenv('DWH_AUTHENTICATION', 'Windows')

import queue
import threading

_CONN_STR = None
_CONN_POOL = queue.Queue(maxsize=10)
_CONN_POOL_LOCK = threading.Lock()

def _get_conn_str():
    """Baut den Connection-String einmalig."""
    global _CONN_STR
    if _CONN_STR:
        return _CONN_STR
    driver = '{ODBC Driver 17 for SQL Server}'
    available = [d for d in pyodbc.drivers() if 'SQL Server' in d]
    if available:
        driver = '{' + available[-1] + '}'
    if DWH_AUTHENTICATION == 'Windows':
        _CONN_STR = (
            f'DRIVER={driver};'
            f'SERVER={DWH_HOST},{DWH_PORT};'
            f'DATABASE={DWH_DATABASE};'
            f'Trusted_Connection=yes;'
            f'TrustServerCertificate=yes;'
        )
    else:
        user = os.getenv('DWH_USER', '')
        password = os.getenv('DWH_PASSWORD', '')
        _CONN_STR = (
            f'DRIVER={driver};'
            f'SERVER={DWH_HOST},{DWH_PORT};'
            f'DATABASE={DWH_DATABASE};'
            f'UID={user};PWD={password};'
            f'TrustServerCertificate=yes;'
        )
    return _CONN_STR

def get_connection():
    """Holt eine Verbindung aus dem Pool oder erstellt eine neue."""
    try:
        conn = _CONN_POOL.get_nowait()
        # Prüfe ob Verbindung noch lebt
        try:
            conn.execute('SELECT 1')
            return conn
        except Exception:
            try: conn.close()
            except Exception: pass
    except queue.Empty:
        pass
    return pyodbc.connect(_get_conn_str(), timeout=30)

def release_connection(conn):
    """Gibt eine Verbindung zurück in den Pool."""
    try:
        _CONN_POOL.put_nowait(conn)
    except queue.Full:
        try: conn.close()
        except Exception: pass


# ─── Reverse-Mapping: Basis-PK → alle Varianten (inkl. sich selbst) ───
# Wird aus MariaDB geladen (config_db.py)
_PK_MAPPING = config_db.PK_MAPPING
_PK_REVERSE = config_db.PK_REVERSE


def expand_pk(produktkuerzel):
    """Gibt Liste aller Produktkürzel-Varianten für ein Basis-PK zurück."""
    return _PK_REVERSE.get(produktkuerzel, [produktkuerzel])


def pk_in_clause(produktkuerzel):
    """Gibt (sql_fragment, params) für IN-Clause zurück.
    Beispiel: ('IN (?,?,?)', ['BBA','BBAb','BBAd'])
    """
    variants = expand_pk(produktkuerzel)
    placeholders = ','.join('?' * len(variants))
    return f'IN ({placeholders})', variants


def pk_expand_sql(sql, produktkuerzel, count=None):
    """Ersetzt alle '= ?' Produktkuerzel-Filter durch 'IN (?,?,...)'.
    Gibt (neues_sql, params_liste) zurück.
    count: Anzahl der '= ?'-Stellen die ersetzt werden sollen (None = alle).
    """
    variants = expand_pk(produktkuerzel)
    placeholders = ','.join('?' * len(variants))
    in_clause = f'IN ({placeholders})'
    new_sql = sql
    params = []
    replaced = 0
    while '= ?' in new_sql:
        if count is not None and replaced >= count:
            break
        new_sql = new_sql.replace('= ?', in_clause, 1)
        params.extend(variants)
        replaced += 1
    return new_sql, params


def query_db(sql, params=None):
    """Führt eine SQL-Abfrage aus und gibt eine Liste von Dicts zurück."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows
    except Exception:
        try: conn.close()
        except Exception: pass
        raise
    else:
        release_connection(conn)


def query_db_multi(queries):
    """Führt mehrere Queries auf EINER Connection aus. queries = [(sql, params), ...]"""
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
            results.append([dict(zip(columns, row)) for row in cursor.fetchall()])
        return results
    except Exception:
        try: conn.close()
        except Exception: pass
        raise
    else:
        release_connection(conn)


# ═══════════════════════════════════════
# Semester-Filter: aktuelles Semester + letzte 6 = 7
# ═══════════════════════════════════════
from datetime import date as _date

def _aktuelles_semester():
    """Gibt das aktuelle Semesterkuerzel im DB-Format zurück (z.B. '2026-SS')."""
    today = _date.today()
    return f"{today.year}-SS" if 3 <= today.month <= 8 else f"{today.year}-WS"

def _semester_filter_7(rows, key='Semesterkuerzel'):
    """Filtert Zeilen auf aktuelles Semester + letzte 6 (max 7 Semester, aufsteigend sortiert)."""
    cur = _aktuelles_semester()
    filtered = [r for r in rows if r[key] <= cur]
    # Letzte 7 einzigartige Semester ermitteln und alle zugehörigen Zeilen behalten
    unique_sems = sorted(set(r[key] for r in filtered))[-7:]
    sem_set = set(unique_sems)
    return [r for r in filtered if r[key] in sem_set]


# ═══════════════════════════════════════
# SQL QUERIES (dynamisch aus config_db generiert)
# ═══════════════════════════════════════

def _build_sql_queries():
    """Baut alle SQL-Queries mit Werten aus der Konfigurations-DB."""
    global SQL_STUDIERENDE_ZEITREIHE, SQL_STUDIERENDE_HSZ, SQL_STUDIERENDE_HSZ_AVG, SQL_AKTIVE_HSZEN
    global SQL_STUDIENGAENGE_LISTE, SQL_STUDIERENDE_AKTUELL

    _excl = config_db.EXCLUDED_HSZ_SQL
    _pk_case_s = config_db._build_pk_case_for_s()
    _jahre_trends = config_db.get_param_int('trends', 'jahre_zurueck', 4)
    _ausrichtung_excl = config_db.get_filter_sql('AUSRICHTUNG_EXCLUDE')
    _hsb_excl = config_db.HSB_EXCLUDE_SQL

    SQL_STUDIERENDE_ZEITREIHE = f"""
    SELECT
        s.Semesterkuerzel,
        RIGHT(s.Semesterkuerzel, 2) AS SemesterTyp,
        LEFT(s.Semesterkuerzel, 4) AS Jahr,
        SUM(CASE WHEN s.Produktkuerzel = ? THEN s.Gesamtstudierende ELSE 0 END) AS Gesamtstudierende_SG,
        CAST(
            SUM(s.Gesamtstudierende) * 1.0 / NULLIF(COUNT(DISTINCT
                CASE WHEN s.Gesamtstudierende > 0 THEN
                    {_pk_case_s}
                END
            ), 0)
        AS DECIMAL(10,1)) AS Gesamtstudierende_FOM_Avg,
        SUM(CASE WHEN s.Produktkuerzel = ? THEN s.Beginner ELSE 0 END) AS Beginner_SG,
        CAST(
            SUM(s.Beginner) * 1.0 / NULLIF(COUNT(DISTINCT
                CASE WHEN s.Gesamtstudierende > 0 THEN
                    {_pk_case_s}
                END
            ), 0)
        AS DECIMAL(10,1)) AS Beginner_FOM_Avg
    FROM BCW_DWH.dwh.C_Studierendenzahlen s
    WHERE s.Institut = 'FOM'
      AND ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})
      AND s.Hochschulzentrum NOT IN ({_excl})
      AND CAST(LEFT(s.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - {_jahre_trends}
      AND s.Semesterkuerzel <= CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    GROUP BY s.Semesterkuerzel
    ORDER BY LEFT(s.Semesterkuerzel, 4),
             CASE WHEN RIGHT(s.Semesterkuerzel, 2) = 'SS' THEN 0 ELSE 1 END
"""

    SQL_STUDIERENDE_HSZ = f"""
    SELECT
        s.Semesterkuerzel,
        RIGHT(s.Semesterkuerzel, 2) AS SemesterTyp,
        LEFT(s.Semesterkuerzel, 4) AS Jahr,
        s.Hochschulzentrum,
        SUM(s.Gesamtstudierende) AS Gesamtstudierende,
        SUM(s.Beginner) AS Beginner
    FROM BCW_DWH.dwh.C_Studierendenzahlen s
    WHERE s.Institut = 'FOM'
      AND s.Produktkuerzel = ?
      AND ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})
      AND s.Hochschulzentrum NOT IN ({_excl})
      AND CAST(LEFT(s.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - {_jahre_trends}
      AND s.Semesterkuerzel <= CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    GROUP BY s.Semesterkuerzel, s.Hochschulzentrum
    ORDER BY CASE WHEN s.Hochschulzentrum = 'DLS' THEN 0 ELSE 1 END, s.Hochschulzentrum, LEFT(s.Semesterkuerzel, 4)
"""

    SQL_STUDIERENDE_HSZ_AVG = f"""
    SELECT
        s.Semesterkuerzel,
        RIGHT(s.Semesterkuerzel, 2) AS SemesterTyp,
        LEFT(s.Semesterkuerzel, 4) AS Jahr,
        s.Hochschulzentrum,
        CAST(SUM(s.Gesamtstudierende) * 1.0 / NULLIF(COUNT(DISTINCT
            CASE WHEN s.Gesamtstudierende > 0 THEN
                {_pk_case_s}
            END
        ), 0) AS DECIMAL(10,1)) AS AvgStudierende,
        CAST(SUM(s.Beginner) * 1.0 / NULLIF(COUNT(DISTINCT
            CASE WHEN s.Beginner > 0 THEN
                {_pk_case_s}
            END
        ), 0) AS DECIMAL(10,1)) AS AvgBeginner
    FROM BCW_DWH.dwh.C_Studierendenzahlen s
    WHERE s.Institut = 'FOM'
      AND ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})
      AND s.Hochschulzentrum NOT IN ({_excl})
      AND CAST(LEFT(s.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - {_jahre_trends}
      AND s.Semesterkuerzel <= CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    GROUP BY s.Semesterkuerzel, s.Hochschulzentrum
"""

    SQL_AKTIVE_HSZEN = f"""
    SELECT Hochschulzentrum FROM (
        SELECT DISTINCT s.Hochschulzentrum
        FROM BCW_DWH.dwh.C_Studierendenzahlen s
        WHERE s.Institut = 'FOM'
          AND s.Produktkuerzel = ?
          AND ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})
          AND s.Gesamtstudierende = 1
          AND CAST(LEFT(s.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - 3
          AND s.Hochschulzentrum NOT IN ({_excl})
    ) t
    ORDER BY CASE WHEN t.Hochschulzentrum = 'DLS' THEN 0 ELSE 1 END, t.Hochschulzentrum
"""

    SQL_STUDIENGAENGE_LISTE = f"""
    SELECT
        sq.Produktkuerzel,
        sq.Studiengang,
        sq.Hochschulbereich,
        sq.HochschulbereichKuerzel,
        sq.Abschluss
    FROM (
        SELECT DISTINCT
            s.Produktkuerzel,
            COALESCE(l.Studiengang, s.Studiengang) AS Studiengang,
            s.Hochschulbereich,
            s.HochschulbereichKuerzel,
            l.Abschluss
        FROM BCW_DWH.dwh.C_Studierendenzahlen s
        LEFT JOIN (
            SELECT DISTINCT Produktkuerzel, Studiengang, Abschluss
            FROM BCW_DWH.dwh.Lehrgaenge
            WHERE Institut = 'FOM'
              AND LehrgangsEnde >= GETDATE()
              AND LehrgangGueltig = 1
        ) l ON l.Produktkuerzel = s.Produktkuerzel
        WHERE s.Institut = 'FOM'
          AND ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})
          AND ISNULL(s.HochschulbereichKuerzel, '') NOT IN ({_hsb_excl}, '')
          AND s.Hochschulzentrum NOT IN ({_excl})
          AND s.Produktkuerzel LIKE '[BM]%'
          AND s.Gesamtstudierende = 1
          AND s.Semesterkuerzel = CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    ) sq
    ORDER BY sq.Hochschulbereich, sq.Studiengang
"""

    SQL_STUDIERENDE_AKTUELL = f"""
    SELECT
        s.Produktkuerzel,
        SUM(s.Gesamtstudierende) AS Gesamtstudierende
    FROM BCW_DWH.dwh.C_Studierendenzahlen s
    WHERE s.Institut = 'FOM'
      AND ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})
      AND s.Hochschulzentrum NOT IN ({_excl})
      AND s.Semesterkuerzel = CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    GROUP BY s.Produktkuerzel
"""

    # ─── PK-Mapping für Studiengangvarianten → Basis-Produktkuerzel ───
    global _PK_CASE
    _PK_CASE = config_db.PK_CASE_SQL

    # Verbleibende Queries mit dynamischen Config-Werten
    global SQL_STAMMDATEN_ALTER

    _jahre_stamm = config_db.get_param_int('stammdaten', 'jahre_zurueck', 2)
    _kohorten_j = config_db.get_param_int('studienerfolg', 'kohorten_jahre', 5)
    _uebergang_j = config_db.get_param_int('uebergang', 'kohorten_jahre', 5)
    _herkunft_j = config_db.get_param_int('herkunft', 'kohorten_jahre', 5)
    _vertiefung_von = config_db.get_param('vertiefung', 'datum_von', '2018-09-01')
    _vertiefung_bis = config_db.get_param('vertiefung', 'datum_bis', '2021-09-01')
    _hz_von = config_db.get_param('hochschulzertifikate', 'datum_von', '2021-08-01')
    _jahre_zuz = config_db.get_param_int('zuzahler', 'jahre_zurueck', 4)
    _sem_anr = config_db.get_param_int('anrechnungen', 'semester_zurueck', 6)
    _sg_trends = config_db.get_param('trends', 'statusgruppe', 'Gesamtstudierende mit UV')
    _sg_stamm_1 = config_db.get_param('stammdaten', 'statusgruppe', 'Beginner mit UV')
    _sg_stamm_2 = config_db.get_param('stammdaten', 'statusgruppe_2', 'Quereinsteiger mit UV')
    _sg_zuz = config_db.get_param('zuzahler', 'statusgruppe', 'Gesamtstudierende mit UV')
    _sg_anr_1 = config_db.get_param('anrechnungen', 'statusgruppe_1', 'Beginner mit UV')
    _sg_anr_2 = config_db.get_param('anrechnungen', 'statusgruppe_2', 'Quereinsteiger mit UV')
    _offene_hs = config_db.OFFENE_HOCHSCHULE_SQL
    _ue_raumids = config_db.get_filter_sql('UE_RAUMID')
    _ue_veransttyp = config_db.get_filter_sql('UE_VERANSTTYP')
    _ue_produktgruppe = config_db.get_filter_sql('UE_PRODUKTGRUPPE')
    _ue_statusrpl = config_db.get_filter_sql('UE_STATUSRPL')
    _vertiefung_art = config_db.get_filter_sql('VERTIEFUNG_ART')
    _vertiefung_fach_excl = config_db.get_filter_sql('VERTIEFUNG_FACH')
    _leistungsart_ignore = config_db.get_filter_sql('LEISTUNGSART_IGNORE')
    _zuzahler_empf = config_db.get_filter_sql('ZUZAHLER_EMPF')
    _zuzahler_kostentyp = config_db.get_filter_values('ZUZAHLER_KOSTENTYP')[0] if config_db.get_filter_values('ZUZAHLER_KOSTENTYP') else 'Arbeitgeber'
    _dual_format = config_db.get_filter_sql('DUAL_STUDIENFORMAT')
    _dual_bildung = config_db.get_filter_values('DUAL_BILDUNGSABSCHNITT')[0] if config_db.get_filter_values('DUAL_BILDUNGSABSCHNITT') else 'Erstausbildung'

    # ─── Stammdaten ───
    SQL_STAMMDATEN_ALTER = f"""
    SELECT
        sz.Semesterkuerzel,
        l.Hochschulzentrum AS HSZ,
        AVG(
            CASE
                WHEN p.Geburtsdatum = '1111-11-11' THEN NULL
                WHEN l.Lehrgangskuerzel = 'BBA WS16 CN-TY' THEN
                    YEAR(CAST('2016-09-01' AS DATE)) - YEAR(p.Geburtsdatum)
                    - CASE WHEN RIGHT(CONVERT(VARCHAR(10), CAST('2016-09-01' AS DATE), 120), 5)
                               < SUBSTRING(CONVERT(VARCHAR(10), p.Geburtsdatum, 120), 6, 5)
                           THEN 1 ELSE 0 END
                ELSE
                    YEAR(CAST(l.LehrgangsStart AS DATE)) - YEAR(p.Geburtsdatum)
                    - CASE WHEN RIGHT(CONVERT(VARCHAR(10), CAST(l.LehrgangsStart AS DATE), 120), 5)
                               < SUBSTRING(CONVERT(VARCHAR(10), p.Geburtsdatum, 120), 6, 5)
                           THEN 1 ELSE 0 END
            END * 1.0
        ) AS DurchschnittsAlter,
        COUNT(*) AS Cnt
    FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
        INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
        INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
        INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
        INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
    WHERE l.Produktkuerzel = ? AND l.Institut = 'FOM'
      AND l.Ausrichtung = 'national'
      AND p.Testperson = 0 AND sg.StatusGruppe IN ('{_sg_stamm_1}', '{_sg_stamm_2}')
      AND se.ImmatrikulationsDatum IS NOT NULL
      AND (se.ExmatrikulationsDatum IS NULL OR se.ExmatrikulationsDatum >= DATEFROMPARTS(YEAR(GETDATE())-{_jahre_stamm}, 3, 1))
      AND CAST(LEFT(sz.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - {_jahre_stamm}
      AND l.Hochschulzentrum NOT IN ({_excl})
    GROUP BY sz.Semesterkuerzel, l.Hochschulzentrum
    ORDER BY sz.Semesterkuerzel
"""

# Ende von _build_sql_queries() – wird am Ende des SQL-Blocks aufgerufen

SQL_STAMMDATEN_DETAIL = """
    WITH basis AS (
        SELECT
            sz.Semesterkuerzel,
            l.Hochschulzentrum AS HSZ,
            p.Geschlecht,
            CASE
                WHEN p.Staatsangehoerigkeit IS NULL THEN 'unbekannt'
                WHEN LTRIM(RTRIM(p.Staatsangehoerigkeit)) = '' THEN 'unbekannt'
                WHEN LOWER(LTRIM(RTRIM(p.Staatsangehoerigkeit))) = 'deutsch' THEN 'deutsch'
                ELSE p.Staatsangehoerigkeit
            END AS Staatsangehoerigkeit,
            si.Berufsausbildung,
            CASE
                WHEN holy.Bildungsabschnitt = 'Erstausbildung' AND holy.Studienformat IN ('ausbildungsintegrierend', 'berufsintegrierend', 'berufsbegleitend +') THEN 1
                ELSE 0
            END AS IstDual,
            CASE WHEN l.ZeitmodellDetail = 'Tages-Studium' THEN 1 ELSE 0 END AS IstTagesstudium,
            se.AnrechnungsGrund,
            CASE
                WHEN sz.Semesterkuerzel = CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
                THEN 'aktuell' ELSE 'rest'
            END AS Zeitraum
        FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
            INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
            LEFT JOIN BCW_STA.mariadb.t_studiengaenge_tn holy ON holy.studiengang_tn_ID = se.StudienEintragID
            LEFT JOIN BCW_DWH.dwh.StudierendenInformationen si ON si.PersonenFID = se.PersonenFID AND si.Institut = l.Institut
            INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
        WHERE l.Produktkuerzel = ? AND l.Institut = 'FOM'
          AND l.Ausrichtung = 'national'
          AND p.Testperson = 0 AND sg.StatusGruppe IN ('Beginner mit UV', 'Quereinsteiger mit UV')
          AND se.ImmatrikulationsDatum IS NOT NULL
          AND (se.ExmatrikulationsDatum IS NULL OR se.ExmatrikulationsDatum >= DATEFROMPARTS(YEAR(GETDATE())-2, 3, 1))
          AND CAST(LEFT(sz.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - 2
          AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
    )
    SELECT
        Zeitraum,
        HSZ,
        COUNT(*) AS Total,
        SUM(CASE WHEN Geschlecht = 'W' THEN 1 ELSE 0 END) AS Weiblich,
        SUM(CASE WHEN Geschlecht = 'M' THEN 1 ELSE 0 END) AS Maennlich,
        SUM(CASE WHEN Staatsangehoerigkeit = 'deutsch' THEN 1 ELSE 0 END) AS Inlaendisch,
        SUM(CASE WHEN Staatsangehoerigkeit <> 'deutsch' AND Staatsangehoerigkeit <> 'unbekannt' THEN 1 ELSE 0 END) AS Auslaendisch,
        SUM(CASE WHEN Staatsangehoerigkeit = 'unbekannt' THEN 1 ELSE 0 END) AS Unbekannt,
        SUM(CASE WHEN IstDual = 1 THEN 1 ELSE 0 END) AS Dual,
        SUM(CASE WHEN IstTagesstudium = 1 THEN 1 ELSE 0 END) AS Tagesstudium,
        SUM(CASE WHEN AnrechnungsGrund IN ('andere BW/IBW', 'andere Fortbildungen', 'eigene BW/IBW', 'eigene Ök', 'Fachkaufleute', 'IHK-Betriebswirt', 'IHK-Fachwirt') THEN 1 ELSE 0 END) AS OffeneHochschule
    FROM basis
    GROUP BY Zeitraum, HSZ
"""

SQL_STAMMDATEN_BERUFSAUSBILDUNG = """
    WITH basis AS (
        SELECT
            si.Berufsausbildung,
            l.Hochschulzentrum AS HSZ,
            CASE
                WHEN sz.Semesterkuerzel = CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
                THEN 'aktuell' ELSE 'rest'
            END AS Zeitraum
        FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
            INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
            LEFT JOIN BCW_DWH.dwh.StudierendenInformationen si ON si.PersonenFID = se.PersonenFID AND si.Institut = l.Institut
            INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
        WHERE l.Produktkuerzel = ? AND l.Institut = 'FOM'
          AND l.Ausrichtung = 'national'
          AND p.Testperson = 0 AND sg.StatusGruppe IN ('Beginner mit UV', 'Quereinsteiger mit UV')
          AND se.ImmatrikulationsDatum IS NOT NULL
          AND (se.ExmatrikulationsDatum IS NULL OR se.ExmatrikulationsDatum >= DATEFROMPARTS(YEAR(GETDATE())-2, 3, 1))
          AND CAST(LEFT(sz.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - 2
          AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
          AND si.Berufsausbildung IS NOT NULL AND si.Berufsausbildung <> '' AND si.Berufsausbildung <> 'Ohne'
    )
    SELECT Zeitraum, HSZ, Berufsausbildung, COUNT(*) AS Cnt
    FROM basis
    GROUP BY Zeitraum, HSZ, Berufsausbildung
    ORDER BY Zeitraum, Cnt DESC
"""

# ─── Studienerfolg (basierend auf StudierendenstatusJeSemester, analog Holy-View) ───
_SE_CTE = """
    WITH LatestStatus AS (
        SELECT
            sjs.StudienEintragFID,
            sjs.Status,
            sjs.Zustand,
            sjs.Fachsemester,
            se.ExmatrikulationsDatum,
            se.ImmatrikulationsDatum,
            se.Exmatrikulationsgrund,
            cea.Ausstiegsstatus,
            l.Produktkuerzel,
            l.Kohorte,
            l.LehrgangsEnde,
            l.Hochschulzentrum,
            ROW_NUMBER() OVER (PARTITION BY sjs.StudienEintragFID ORDER BY sem.SemesterStart DESC) as rn
        FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
        JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
        JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
        JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
        JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
        LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg cea ON cea.StudienEintragID = se.StudienEintragID
        WHERE sem.SemesterStart < GETDATE()
          AND l.Institut = 'FOM'
          AND p.Testperson = 0
          AND se.ImmatrikulationsDatum <= GETDATE()
          AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
          AND LEFT(sjs.Status, 2) <> 'VT'
          AND (cea.Ausstiegsstatus NOT IN ('-', 'V', 'US') OR sjs.Zustand = '1')
          AND sjs.Status NOT IN ('Vorkurs','Urlaubssemester')
          AND l.Produktkuerzel NOT IN ('WBS','GBA')
          AND l.Ausrichtung = 'national'
          AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
          AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-10,GETDATE())) AS VARCHAR),'-WS')
    )
"""

_SE_CLUSTER_CASE = """
        CASE
            WHEN Ausstiegsstatus = 'KoopWG' THEN NULL
            WHEN Ausstiegsstatus = 'K' AND Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN NULL
            WHEN Ausstiegsstatus = 'K' THEN 'Abbrecher'
            WHEN Ausstiegsstatus IN ('WE', 'WPO', 'WSGO', 'WUS') THEN 'Wechsler'
            WHEN Ausstiegsstatus = 'A' THEN 'Absolvent'
            WHEN Ausstiegsstatus = 'US' THEN NULL
            WHEN Ausstiegsstatus = 'V' THEN 'Eingeschrieben'
            WHEN Ausstiegsstatus = '-' THEN 'Eingeschrieben'
            WHEN Ausstiegsstatus IS NULL THEN 'Eingeschrieben'
            ELSE NULL
        END"""

_SE_RSZ_CASE = """
        CASE
            WHEN Ausstiegsstatus = 'V' THEN 1
            ELSE 0
        END"""

_SE_KOHORTE_FILTER = """
      AND Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
      AND Kohorte <= CONCAT(CAST(YEAR(GETDATE()) AS VARCHAR), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)"""

SQL_FACHSEMESTER = _SE_CTE + """
    SELECT
        CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END AS Fachsem,
""" + _SE_CLUSTER_CASE + """ AS AusstiegsCluster,
""" + _SE_RSZ_CASE + """ AS RSZ,
        Hochschulzentrum AS HSZ,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = ?
""" + _SE_KOHORTE_FILTER + """
    GROUP BY CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END,
""" + _SE_CLUSTER_CASE + """,
""" + _SE_RSZ_CASE + """,
        Hochschulzentrum
    ORDER BY Fachsem
"""

SQL_FACHSEMESTER_FOM = _SE_CTE + """
    SELECT
        CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END AS Fachsem,
""" + _SE_CLUSTER_CASE + """ AS AusstiegsCluster,
""" + _SE_RSZ_CASE + """ AS RSZ,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1
""" + _SE_KOHORTE_FILTER + """
    GROUP BY CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END,
""" + _SE_CLUSTER_CASE + """,
""" + _SE_RSZ_CASE + """
    ORDER BY Fachsem
"""

SQL_VERLAENGERUNG = _SE_CTE + """
    SELECT
        CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT) AS VerlaengerungsSem,
        Hochschulzentrum AS HSZ,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = ?
      AND Ausstiegsstatus = 'A'
""" + _SE_KOHORTE_FILTER + """
    GROUP BY CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT),
        Hochschulzentrum
    ORDER BY VerlaengerungsSem
"""

SQL_VERLAENGERUNG_FOM = _SE_CTE + """
    SELECT
        CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT) AS VerlaengerungsSem,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1
      AND Ausstiegsstatus = 'A'
""" + _SE_KOHORTE_FILTER + """
    GROUP BY CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT)
    ORDER BY VerlaengerungsSem
"""

# ─── Übergang B→M ───
SQL_UEBERGANG = """
    WITH bachelor_absolventen AS (
        SELECT
            se_b.PersonenFID,
            l_b.Produktkuerzel AS B_PK,
            l_b.HochschulzentrumKuerzel AS B_HSZ_K,
            l_b.Hochschulzentrum AS B_HSZ,
            l_b.Kohorte AS B_Kohorte,
            se_b.ExmatrikulationsDatum AS B_ExDatum,
            se_b.ImmatrikulationsDatum AS B_ImDatum
        FROM BCW_DWH.dwh.StudienEintraege se_b
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_b ON l_b.LehrgangsID = se_b.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.Personen p_b ON p_b.PersonenID = se_b.PersonenFID
            LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_b ON c_b.StudienEintragID = se_b.StudienEintragID
        WHERE l_b.Institut = 'FOM'
          AND p_b.Testperson = 0
          AND l_b.Produktkuerzel = ?
          AND l_b.Ausrichtung = 'national'
          AND l_b.Produktart LIKE 'Bachelor%'
          AND (
              c_b.Ausstiegsstatus = 'A'
              OR (c_b.StudienEintragID IS NULL AND se_b.Exmatrikulationsgrund LIKE '1 %')
          )
          AND se_b.AbschlussNote > 0.1
          AND se_b.ImmatrikulationsDatum < se_b.ExmatrikulationsDatum
          AND l_b.LehrgangsEnde < GETDATE()
          AND l_b.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -5, GETDATE())) AS VARCHAR), '-WS')
          AND l_b.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
    ),
    master_einschreibungen AS (
        SELECT
            se_m.PersonenFID,
            l_m.Produktkuerzel AS M_PK,
            l_m.Studiengang AS M_SG,
            l_m.HochschulzentrumKuerzel AS M_HSZ_K,
            l_m.Hochschulzentrum AS M_HSZ,
            se_m.ImmatrikulationsDatum AS M_ImDatum
        FROM BCW_DWH.dwh.StudienEintraege se_m
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_m ON l_m.LehrgangsID = se_m.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_m ON c_m.StudienEintragID = se_m.StudienEintragID
                AND c_m.Einstiegsstatus IS NOT NULL
        WHERE l_m.Institut = 'FOM'
          AND l_m.Ausrichtung = 'national'
          AND l_m.Produktart LIKE 'Master%'
          AND se_m.ImmatrikulationsDatum < se_m.ExmatrikulationsDatum
    )
    SELECT
        ba.PersonenFID, ba.B_PK, ba.B_HSZ_K, ba.B_HSZ, ba.B_Kohorte, ba.B_ExDatum, ba.B_ImDatum,
        me.M_PK, me.M_SG, me.M_HSZ_K, me.M_HSZ, me.M_ImDatum
    FROM bachelor_absolventen ba
        LEFT JOIN master_einschreibungen me ON me.PersonenFID = ba.PersonenFID
            AND ba.B_ImDatum < me.M_ImDatum
"""

SQL_UEBERGANG_FOM = """
    WITH bachelor_absolventen AS (
        SELECT
            se_b.PersonenFID,
            l_b.Produktkuerzel AS B_PK,
            l_b.HochschulzentrumKuerzel AS B_HSZ_K,
            l_b.Hochschulzentrum AS B_HSZ,
            l_b.Kohorte AS B_Kohorte,
            se_b.ExmatrikulationsDatum AS B_ExDatum,
            se_b.ImmatrikulationsDatum AS B_ImDatum
        FROM BCW_DWH.dwh.StudienEintraege se_b
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_b ON l_b.LehrgangsID = se_b.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.Personen p_b ON p_b.PersonenID = se_b.PersonenFID
            LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_b ON c_b.StudienEintragID = se_b.StudienEintragID
        WHERE l_b.Institut = 'FOM'
          AND p_b.Testperson = 0
          AND l_b.Ausrichtung = 'national'
          AND l_b.Produktart LIKE 'Bachelor%'
          AND (
              c_b.Ausstiegsstatus = 'A'
              OR (c_b.StudienEintragID IS NULL AND se_b.Exmatrikulationsgrund LIKE '1 %')
          )
          AND se_b.AbschlussNote > 0.1
          AND se_b.ImmatrikulationsDatum < se_b.ExmatrikulationsDatum
          AND l_b.LehrgangsEnde < GETDATE()
          AND l_b.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -5, GETDATE())) AS VARCHAR), '-WS')
          AND l_b.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
    ),
    master_einschreibungen AS (
        SELECT
            se_m.PersonenFID,
            l_m.Produktkuerzel AS M_PK,
            l_m.Studiengang AS M_SG,
            l_m.HochschulzentrumKuerzel AS M_HSZ_K,
            l_m.Hochschulzentrum AS M_HSZ,
            se_m.ImmatrikulationsDatum AS M_ImDatum
        FROM BCW_DWH.dwh.StudienEintraege se_m
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_m ON l_m.LehrgangsID = se_m.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_m ON c_m.StudienEintragID = se_m.StudienEintragID
                AND c_m.Einstiegsstatus IS NOT NULL
        WHERE l_m.Institut = 'FOM'
          AND l_m.Ausrichtung = 'national'
          AND l_m.Produktart LIKE 'Master%'
          AND se_m.ImmatrikulationsDatum < se_m.ExmatrikulationsDatum
    )
    SELECT
        ba.PersonenFID, ba.B_PK, ba.B_HSZ_K, ba.B_HSZ, ba.B_Kohorte, ba.B_ExDatum, ba.B_ImDatum,
        me.M_PK, me.M_SG, me.M_HSZ_K, me.M_HSZ, me.M_ImDatum
    FROM bachelor_absolventen ba
        LEFT JOIN master_einschreibungen me ON me.PersonenFID = ba.PersonenFID
            AND ba.B_ImDatum < me.M_ImDatum
"""

# ─── Herkunft M←B ───
SQL_HERKUNFT = """
    WITH master_beginner AS (
        SELECT
            se_m.PersonenFID,
            l_m.Produktkuerzel AS M_PK,
            l_m.HochschulzentrumKuerzel AS M_HSZ_K,
            l_m.Hochschulzentrum AS M_HSZ,
            l_m.Kohorte AS M_Kohorte,
            se_m.ImmatrikulationsDatum AS M_ImDatum
        FROM BCW_DWH.dwh.StudienEintraege se_m
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_m ON l_m.LehrgangsID = se_m.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.Personen p_m ON p_m.PersonenID = se_m.PersonenFID
        WHERE l_m.Institut = 'FOM'
          AND l_m.Ausrichtung = 'national'
          AND p_m.Testperson = 0
          AND l_m.Produktkuerzel = ?
          AND l_m.Ausrichtung = 'national'
          AND l_m.Produktart LIKE 'Master%'
          AND l_m.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -5, GETDATE())) AS VARCHAR), '-WS')
          AND l_m.Kohorte <= CONCAT(CAST(YEAR(GETDATE()) AS VARCHAR), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
          AND l_m.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
          AND se_m.ImmatrikulationsDatum < se_m.ExmatrikulationsDatum
    ),
    bachelor_abschluss AS (
        SELECT
            se_b.PersonenFID,
            l_b.Produktkuerzel AS B_PK,
            l_b.Studiengang AS B_SG,
            l_b.StudiengangFamilie AS B_Familie,
            l_b.HochschulzentrumKuerzel AS B_HSZ_K,
            l_b.Hochschulzentrum AS B_HSZ,
            se_b.ExmatrikulationsDatum AS B_ExDatum,
            se_b.ImmatrikulationsDatum AS B_ImDatum
        FROM BCW_DWH.dwh.StudienEintraege se_b
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_b ON l_b.LehrgangsID = se_b.LehrgangsFID
            LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_b ON c_b.StudienEintragID = se_b.StudienEintragID
        WHERE l_b.Institut = 'FOM'
          AND l_b.Ausrichtung = 'national'
          AND l_b.Produktart LIKE 'Bachelor%'
          AND (
              c_b.Ausstiegsstatus = 'A'
              OR (c_b.StudienEintragID IS NULL AND se_b.Exmatrikulationsgrund LIKE '1 %')
          )
          AND se_b.AbschlussNote > 0.1
          AND se_b.ImmatrikulationsDatum < se_b.ExmatrikulationsDatum
    )
    SELECT
        mb.PersonenFID, mb.M_PK, mb.M_HSZ_K, mb.M_HSZ, mb.M_Kohorte, mb.M_ImDatum,
        ba.B_PK, ba.B_SG, ba.B_Familie, ba.B_HSZ_K, ba.B_HSZ, ba.B_ExDatum
    FROM master_beginner mb
        LEFT JOIN bachelor_abschluss ba ON ba.PersonenFID = mb.PersonenFID
            AND ba.B_ImDatum < mb.M_ImDatum
"""

# ─── Zuzahler (Referenz-Logik: t_ZahlungenTn + t_rechnungen) ───
# Semester-Filter gleich wie Gesamtstudierende-Tab: YEAR(GETDATE()) - 4, <= aktuelles Semester
_ZUZAHLER_GS_CTE = """
    gs AS (
        SELECT DISTINCT
            sz.Semesterkuerzel,
            se.StudienEintragID,
            se.PersonenFID,
            p.Nachname,
            CASE
                WHEN RIGHT(sz.Semesterkuerzel, 2) = 'SS'
                    THEN CAST(CONCAT(LEFT(sz.Semesterkuerzel, 4), '-03-01') AS DATE)
                ELSE CAST(CONCAT(LEFT(sz.Semesterkuerzel, 4), '-09-01') AS DATE)
            END AS SemesterStart
        FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
        INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
        INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
        INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
        INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
        WHERE l.Institut = 'FOM'
          AND p.Testperson = 0
          AND sg.StatusGruppe = 'Gesamtstudierende mit UV'
          AND CAST(LEFT(sz.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - 4
          AND sz.Semesterkuerzel <= CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
          AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
          AND l.Ausrichtung = 'national'
          {pk_filter}
    )
"""

_ZUZAHLER_MAIN = """
    SELECT
        gs.Semesterkuerzel,
        COUNT(DISTINCT gs.StudienEintragID) AS Total,
        COUNT(DISTINCT CASE
            WHEN ztn.ID IS NOT NULL OR r_match.RechnungsID IS NOT NULL THEN gs.StudienEintragID
        END) AS Zuzahler
    FROM gs
    LEFT JOIN BCW_STA.mariadb.t_ZahlungenTn ztn
        ON ztn.StudiengaengeTNID = gs.StudienEintragID
        AND gs.SemesterStart BETWEEN TRY_CAST(ztn.LaufzeitVon AS DATE) AND TRY_CAST(ztn.LaufzeitBis AS DATE)
        AND ztn.KostenUebernahmeDurch = 'Arbeitgeber'
    LEFT JOIN (
        SELECT r.RechnungsID, r.PersonenFID,
               TRY_CAST(r.VonTeilnahme AS DATE) AS VonTeilnahme,
               TRY_CAST(r.BisTeilnahme AS DATE) AS BisTeilnahme,
               TRY_CAST(r.Ausgeschieden AS DATE) AS Ausgeschieden,
               r.RechEmpfaenger, r.MatrikelNr, r.DebitorenNr
        FROM BCW_STA.mariadb.t_rechnungen r
        WHERE NOT EXISTS (
            SELECT 1 FROM BCW_STA.mariadb.t_rechnungen_deaktiviert d WHERE d.RechnungsFID = r.RechnungsID
        )
        AND r.MatrikelNr <> r.DebitorenNr
        AND LTRIM(RTRIM(r.RechEmpfaenger)) NOT IN ('Mitarbeiter')
    ) r_match ON r_match.PersonenFID = gs.PersonenFID
        AND r_match.VonTeilnahme <= gs.SemesterStart
        AND r_match.BisTeilnahme >= gs.SemesterStart
        AND r_match.Ausgeschieden >= gs.SemesterStart
        AND gs.Nachname IS NOT NULL AND gs.Nachname <> ''
        AND LTRIM(RTRIM(r_match.RechEmpfaenger)) NOT LIKE '%' + gs.Nachname + '%'
    GROUP BY gs.Semesterkuerzel
    ORDER BY gs.Semesterkuerzel
"""

def _build_zuzahler_sql(pk_filter_clause):
    """Baut die Zuzahler-SQL mit dem angegebenen PK-Filter."""
    gs_cte = _ZUZAHLER_GS_CTE.replace('{pk_filter}', pk_filter_clause)
    return f"WITH {gs_cte} {_ZUZAHLER_MAIN}"

SQL_ZUZAHLER = _build_zuzahler_sql("AND l.Produktkuerzel = ?")
SQL_ZUZAHLER_FOM = _build_zuzahler_sql("")

# Top10 wird jetzt im Endpoint via Temp-Tabellen berechnet (siehe zuzahler())

# ─── Vertiefungsrichtungen + Wahlpflichtmodule (pro Semester) ───
SQL_VERTIEFUNGSRICHTUNGEN = """
    SELECT
        CASE
            WHEN mc.Art = 'Vertiefungsrichtung' THEN 'Vertiefungsrichtung'
            ELSE 'Wahlpflichtmodul'
        END AS Wahlart,
        fg.Fachgebiet AS Vertiefungsname,
        mb.Bezeichnung AS Modulname,
        CASE
            WHEN MONTH(TRY_CAST(pe.AnmeldeDatum AS DATE)) >= 9
                THEN CONCAT(YEAR(TRY_CAST(pe.AnmeldeDatum AS DATE)), '-WS')
            WHEN MONTH(TRY_CAST(pe.AnmeldeDatum AS DATE)) >= 3
                THEN CONCAT(YEAR(TRY_CAST(pe.AnmeldeDatum AS DATE)), '-SS')
            ELSE CONCAT(YEAR(TRY_CAST(pe.AnmeldeDatum AS DATE))-1, '-WS')
        END AS Semesterkuerzel,
        COUNT(DISTINCT n.StudienEintragFID) AS Anzahl
    FROM BCW_DWH.dwh.Noten n
        INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = n.StudienEintragFID
        INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
        INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
        INNER JOIN BCW_STA.mariadb.t_pruefungsergebnisse pe ON pe.PruefungsErgebnisID = n.PruefungsErgebnisFID
        INNER JOIN BCW_STA.mariadb.t_modulbeschreibung mb ON mb.ModulID = n.ModulFID
        INNER JOIN BCW_STA.mariadb.t_mn_modulcontainer_modul mcm ON mcm.ModulbeschreibungFID = mb.ModulID
        INNER JOIN BCW_STA.mariadb.t_modulcontainer mc ON mc.ModulcontainerID = mcm.ModulcontainerFID
        INNER JOIN BCW_STA.mariadb.t_fachgebiete fg ON fg.FachgebietID = mc.FachgebietFID
        INNER JOIN BCW_STA.mariadb.MnModulContainerGruppenProduktzuordnung pz
            ON pz.ModulContainerGruppenFid = mc.ModulcontainerGruppeID
    WHERE pz.Produktkuerzel = ?
      AND l.Produktkuerzel = ?
      AND l.Institut = 'FOM'
      AND l.Ausrichtung = 'national'
      AND l.Produktart IN ('Bachelor-Studiengänge', 'Master-Studiengänge')
      AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
      AND p.Testperson = 0
      AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
      AND mc.Art = 'Vertiefungsrichtung'
      AND pe.Anerkannt IN ('N', 'Z')
      AND fg.Fachgebiet NOT IN ('General Studies Wahlmodul ZEUGNISSE', N'Zusatzwahlfächer')
      AND fg.Fachgebiet LIKE '%Vertiefung%'
      AND TRY_CAST(pe.AnmeldeDatum AS DATE) >= DATEADD(YEAR, -3, GETDATE())
      AND TRY_CAST(pe.AnmeldeDatum AS DATE) < GETDATE()
    GROUP BY
        CASE WHEN mc.Art = 'Vertiefungsrichtung' THEN 'Vertiefungsrichtung' ELSE 'Wahlpflichtmodul' END,
        fg.Fachgebiet, mb.Bezeichnung,
        CASE
            WHEN MONTH(TRY_CAST(pe.AnmeldeDatum AS DATE)) >= 9
                THEN CONCAT(YEAR(TRY_CAST(pe.AnmeldeDatum AS DATE)), '-WS')
            WHEN MONTH(TRY_CAST(pe.AnmeldeDatum AS DATE)) >= 3
                THEN CONCAT(YEAR(TRY_CAST(pe.AnmeldeDatum AS DATE)), '-SS')
            ELSE CONCAT(YEAR(TRY_CAST(pe.AnmeldeDatum AS DATE))-1, '-WS')
        END
    ORDER BY
        CASE WHEN mc.Art = 'Vertiefungsrichtung' THEN 'Vertiefungsrichtung' ELSE 'Wahlpflichtmodul' END,
        fg.Fachgebiet, mb.Bezeichnung, Semesterkuerzel
"""

# ─── Hochschulzertifikate (ab WS21, pro Block) ───
SQL_HOCHSCHULZERTIFIKATE = """
    WITH hz_data AS (
        SELECT
            CASE
                WHEN MONTH(l_hz.LehrgangsStart) >= 9
                    THEN CONCAT(YEAR(l_hz.LehrgangsStart)+1, '-02')
                WHEN MONTH(l_hz.LehrgangsStart) >= 3
                    THEN CONCAT(YEAR(l_hz.LehrgangsStart), '-08')
                ELSE CONCAT(YEAR(l_hz.LehrgangsStart), '-02')
            END AS Block,
            LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                sta_l.Lehrgangsname,
                'Hochschulzertifikat', ''),
                'Spezialisierungskurs', ''),
                'Spezialisierungkurs', ''),
                CHAR(13), ''),
                CHAR(10), ''))) AS Zertifikat,
            se_hz.PersonenFID
        FROM BCW_DWH.dwh.StudienEintraege se_hz
        INNER JOIN BCW_DWH.dwh.Lehrgaenge l_hz ON l_hz.LehrgangsID = se_hz.LehrgangsFID
        INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se_hz.PersonenFID
        INNER JOIN BCW_STA.mariadb.t_lehrgaenge sta_l ON sta_l.LehrgangsNr = l_hz.LehrgangsID
        INNER JOIN BCW_DWH.dwh.StudienEintraege se_main ON se_main.PersonenFID = se_hz.PersonenFID
            AND se_main.StudienEintragID <> se_hz.StudienEintragID
        INNER JOIN BCW_DWH.dwh.Lehrgaenge l_main ON l_main.LehrgangsID = se_main.LehrgangsFID
        WHERE l_hz.Produktart = 'Hochschulzertifikat' AND l_hz.Institut = 'FOM'
          AND p.Testperson = 0
          AND l_main.Institut = 'FOM'
          AND l_main.Produktkuerzel = ?
          AND l_main.Ausrichtung = 'national'
          AND l_main.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
          AND l_hz.LehrgangsStart >= DATEADD(YEAR, -3, GETDATE())
          AND ISNULL(se_hz.Exmatrikulationsgrund, '') NOT LIKE '0[_]%'
    )
    SELECT Block, Zertifikat, COUNT(DISTINCT PersonenFID) AS Anzahl
    FROM hz_data
    WHERE Zertifikat IS NOT NULL AND Zertifikat <> ''
    GROUP BY Block, Zertifikat
    ORDER BY Zertifikat, Block
"""

# ─── UEs (Raumplan) ───
SQL_UES = """
    WITH ModulSemester AS (
        SELECT ModulFID, VerlaufSemester AS Fachsemester
        FROM (
            SELECT ModulFID, VerlaufSemester,
                   ROW_NUMBER() OVER (PARTITION BY ModulFID ORDER BY VerlaufsplanentwurfVersionID DESC) AS rn
            FROM BCW_DWH.dwh.Verlaufsplaene
            WHERE ProduktkuerzelVerlaufsplan = ?
              AND VerlaufSemester IS NOT NULL
        ) ranked
        WHERE rn = 1
    )
    SELECT
        temp.ModulFID,
        ms.Fachsemester,
        temp.UETyp,
        SUM(temp.UE) AS TotalUE
    FROM (
        SELECT
            b.BuchungsID,
            b.UE,
            ks.ModulFID,
            CASE
                WHEN b.Veranstaltungstyp = 'Webinar' THEN 'virtuell'
                WHEN r.Raum LIKE '%Webinar%' OR r.Raum LIKE '%webinar%' THEN 'virtuell'
                WHEN r.Raum = 'folgt' OR r.Raum = '' OR r.Raum IS NULL THEN 'folgt'
                ELSE 'praxis'
            END AS UETyp
        FROM BCW_STA.mariadb.t_buchungen b
            INNER JOIN BCW_STA.mariadb.t_kurs_basisdaten kbd ON kbd.KursBasisdatenID = b.KursBasisdatenFID
            INNER JOIN BCW_STA.mariadb.t_kurs_splittings ks ON ks.KursBasisdatenFID = kbd.KursBasisdatenID
                AND ks.MainEntry = 'Y'
            INNER JOIN BCW_STA.mariadb.t_lehrgaenge l ON l.LehrgangsNr = ks.LehrgangsFID
            INNER JOIN BCW_STA.mariadb.t_raeume r ON r.RaumID = b.RaumFID
            LEFT JOIN BCW_STA.mariadb.t_testpersonen tp ON tp.PersonenFID = b.ReferentenFID
        WHERE l.Produktkuerzel = ?
          AND l.Institut = 'FOM'
          AND l.Ausrichtung = 'national'
          AND l.Produktgruppe IN ('Studium','Akademische Weiterbildung')
          AND l.StatusRPL IN ('A','P')
          AND b.UE > 0
          AND b.Vorlauf = 'N'
          AND b.Veranstaltungstyp NOT IN ('Sonderveranstaltung')
          AND b.Von NOT BETWEEN '00:00' AND '07:00'
          AND r.RaumID NOT IN (274,285,349,845,1608)
          AND tp.PersonenFID IS NULL
          AND TRY_CAST(l.DauerBis AS DATE) >= GETDATE()
          AND TRY_CAST(b.Datum AS DATE) >= CASE WHEN MONTH(GETDATE()) >= 9 THEN DATEFROMPARTS(YEAR(GETDATE()),9,1)
                                                  WHEN MONTH(GETDATE()) >= 3 THEN DATEFROMPARTS(YEAR(GETDATE()),3,1)
                                                  ELSE DATEFROMPARTS(YEAR(GETDATE())-1,9,1) END
          AND TRY_CAST(b.Datum AS DATE) < CASE WHEN MONTH(GETDATE()) >= 9 THEN DATEFROMPARTS(YEAR(GETDATE())+1,3,1)
                                                 WHEN MONTH(GETDATE()) >= 3 THEN DATEFROMPARTS(YEAR(GETDATE()),9,1)
                                                 ELSE DATEFROMPARTS(YEAR(GETDATE()),3,1) END
        GROUP BY b.BuchungsID, b.UE, ks.ModulFID, b.Veranstaltungstyp, r.Raum
    ) AS temp
    LEFT JOIN ModulSemester ms ON ms.ModulFID = temp.ModulFID
    GROUP BY temp.ModulFID, ms.Fachsemester, temp.UETyp
    ORDER BY ms.Fachsemester, temp.UETyp
"""

# SQL um fehlende Module per VP (alle Aliases) nachzuschlagen
SQL_VP_ALIASES_SEMESTER = """
    SELECT ModulFID, VerlaufSemester AS Fachsemester
    FROM (
        SELECT ModulFID, VerlaufSemester,
               ROW_NUMBER() OVER (PARTITION BY ModulFID ORDER BY VerlaufsplanentwurfVersionID DESC) AS rn
        FROM BCW_DWH.dwh.Verlaufsplaene
        WHERE ProduktkuerzelVerlaufsplan IN ({pk_placeholders})
          AND VerlaufSemester IS NOT NULL
          AND ModulFID IN ({mod_placeholders})
    ) ranked
    WHERE rn = 1
"""

# SQL um fehlende Module per Grow nachzuschlagen (nur für bestimmte ModulIDs)
SQL_GROW_SEMESTER = """
    SELECT ModulID, MIN(Semester) AS Fachsemester
    FROM BCW_STA.mariadb.GrowPositionVerlaufsplanElemente
    WHERE Semester IS NOT NULL
      AND ModulID IN ({placeholders})
    GROUP BY ModulID
"""

# ─── Rahmendaten ───
SQL_RAHMENDATEN = """
    SELECT DISTINCT
        l.ZeitmodellDetail AS Zeitmodell,
        MIN(l.LehrgangsStart) AS ErstesAngebot
    FROM BCW_DWH.dwh.Lehrgaenge l
    WHERE l.Produktkuerzel = ?
      AND l.Institut = 'FOM'
      AND l.Ausrichtung = 'national'
      AND l.LehrgangGueltig = 1
      AND l.LehrgangsStart <= GETDATE()
      AND l.LehrgangsEnde >= GETDATE()
      AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
      AND l.ZeitmodellDetail IS NOT NULL AND l.ZeitmodellDetail <> '' AND l.ZeitmodellDetail <> 'keine Angabe'
    GROUP BY l.ZeitmodellDetail
"""

SQL_STUDIENFORMATE = """
    SELECT DISTINCT tl.Studienformat
    FROM BCW_STA.mariadb.t_lehrgaenge tl
    WHERE tl.Produktkuerzel = ?
      AND tl.Institut = 'FOM'
      AND tl.Ausrichtung = 'national'
      AND TRY_CAST(tl.DauerVon AS DATE) <= GETDATE()
      AND TRY_CAST(tl.DauerBis AS DATE) >= GETDATE()
      AND tl.Studienformat IS NOT NULL AND tl.Studienformat <> ''
"""

SQL_DEKAN = """
    SELECT TOP 1 p.TitelDeutsch, p.Vorname, p.Nachname
    FROM BCW_DWH.dwh.Verlaufsplaene v
    INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = v.DekanFID
    WHERE v.ProduktkuerzelVerlaufsplan = ?
      AND v.DekanFID IS NOT NULL AND v.DekanFID > 0
      AND p.Nachname IS NOT NULL AND p.Nachname <> '- kein Nachname -'
"""

# ─── Excel-Rahmendaten (Akkreditierung) ───
# Deaktiviert: Akkreditierungsdatum bleibt vorerst leer
EXCEL_RAHMENDATEN = {}


def _patch_remaining_queries():
    """Ersetzt hart-codierte Config-Werte in den verbleibenden SQL-Strings durch DB-Werte."""
    import sys
    module = sys.modules[__name__]

    # Config-Werte laden
    _excl = config_db.EXCLUDED_HSZ_SQL
    _ausrichtung_excl = config_db.get_filter_sql('AUSRICHTUNG_EXCLUDE')
    _offene_hs = config_db.OFFENE_HOCHSCHULE_SQL
    _sg_stamm_1 = config_db.get_param('stammdaten', 'statusgruppe', 'Beginner mit UV')
    _sg_stamm_2 = config_db.get_param('stammdaten', 'statusgruppe_2', 'Quereinsteiger mit UV')
    _sg_zuz = config_db.get_param('zuzahler', 'statusgruppe', 'Gesamtstudierende mit UV')
    _sg_anr_1 = config_db.get_param('anrechnungen', 'statusgruppe_1', 'Beginner mit UV')
    _sg_anr_2 = config_db.get_param('anrechnungen', 'statusgruppe_2', 'Quereinsteiger mit UV')
    _jahre_stamm = str(config_db.get_param_int('stammdaten', 'jahre_zurueck', 2))
    _kohorten_j = str(config_db.get_param_int('studienerfolg', 'kohorten_jahre', 5))
    _uebergang_j = str(config_db.get_param_int('uebergang', 'kohorten_jahre', 5))
    _herkunft_j = str(config_db.get_param_int('herkunft', 'kohorten_jahre', 5))
    _jahre_zuz = str(config_db.get_param_int('zuzahler', 'jahre_zurueck', 4))
    _vertiefung_von = config_db.get_param('vertiefung', 'datum_von', '2018-09-01')
    _vertiefung_bis = config_db.get_param('vertiefung', 'datum_bis', '2021-09-01')
    _hz_von = config_db.get_param('hochschulzertifikate', 'datum_von', '2021-08-01')
    _ue_raumids = config_db.get_filter_sql('UE_RAUMID')
    _ue_veransttyp = config_db.get_filter_sql('UE_VERANSTTYP')
    _ue_produktgruppe = config_db.get_filter_sql('UE_PRODUKTGRUPPE')
    _ue_statusrpl = config_db.get_filter_sql('UE_STATUSRPL')
    _vertiefung_art = config_db.get_filter_sql('VERTIEFUNG_ART')
    _vertiefung_fach_excl = config_db.get_filter_sql('VERTIEFUNG_FACH')
    _leistungsart_ignore = config_db.get_filter_sql('LEISTUNGSART_IGNORE')
    _zuzahler_empf = config_db.get_filter_sql('ZUZAHLER_EMPF')
    _zuzahler_kostentyp = config_db.get_filter_values('ZUZAHLER_KOSTENTYP')[0] if config_db.get_filter_values('ZUZAHLER_KOSTENTYP') else 'Arbeitgeber'
    _dual_format = config_db.get_filter_sql('DUAL_STUDIENFORMAT')
    _dual_bildung = config_db.get_filter_values('DUAL_BILDUNGSABSCHNITT')[0] if config_db.get_filter_values('DUAL_BILDUNGSABSCHNITT') else 'Erstausbildung'

    # Definiere Ersetzungsregeln: (altes_pattern, neues_pattern)
    replacements = [
        # Excluded Hochschulzentren
        ("'Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg'", _excl),
        # Ausrichtung OBS
        ("ISNULL(s.Ausrichtung, '') <> 'OBS'", f"ISNULL(s.Ausrichtung, '') NOT IN ({_ausrichtung_excl})"),
        # StatusGruppe Stammdaten (Beginner + Quereinsteiger)
        ("sg.StatusGruppe IN ('Beginner mit UV', 'Quereinsteiger mit UV')", f"sg.StatusGruppe IN ('{_sg_stamm_1}', '{_sg_stamm_2}')"),
        # StatusGruppe Anrechnungen
        ("sg.StatusGruppe IN ('Beginner mit UV', 'Quereinsteiger mit UV')", f"sg.StatusGruppe IN ('{_sg_anr_1}', '{_sg_anr_2}')"),
        # Offene Hochschule
        ("AnrechnungsGrund IN ('andere BW/IBW', 'andere Fortbildungen', 'eigene BW/IBW', 'eigene Ök', 'Fachkaufleute', 'IHK-Betriebswirt', 'IHK-Fachwirt')",
         f"AnrechnungsGrund IN ({_offene_hs})"),
        # Vertiefung: Container-Arten
        ("mc.Art IN ('Vertiefungsrichtung', 'Wahlpflichtmodul', 'Wahlmodul')", f"mc.Art IN ({_vertiefung_art})"),
        # Vertiefung: Fachgebiete exclude
        ("fg.Fachgebiet NOT IN ('General Studies Wahlmodul ZEUGNISSE', N'Zusatzwahlfächer')", f"fg.Fachgebiet NOT IN ({_vertiefung_fach_excl})"),
        # Vertiefung: Datum
        (">= '2018-09-01'", f">= '{_vertiefung_von}'"),
        ("< '2021-09-01'", f"< '{_vertiefung_bis}'"),
        # Hochschulzertifikate Datum
        (">= '2021-08-01'", f">= '{_hz_von}'"),
        # UE: Raum-IDs
        ("r.RaumID NOT IN (274,285,349,845,1608)", f"r.RaumID NOT IN ({_ue_raumids})"),
        # UE: Veranstaltungstypen
        ("b.Veranstaltungstyp NOT IN ('Sonderveranstaltung')", f"b.Veranstaltungstyp NOT IN ({_ue_veransttyp})"),
        # UE: Produktgruppen
        ("l.Produktgruppe IN ('Studium','Akademische Weiterbildung')", f"l.Produktgruppe IN ({_ue_produktgruppe})"),
        # UE: StatusRPL
        ("l.StatusRPL IN ('A','P')", f"l.StatusRPL IN ({_ue_statusrpl})"),
        # Leistungsarten ignorieren
        ("la.LeistungsArtAnzeigeName NOT IN ('Einschreibehindernispruefung', 'Kooperation')", f"la.LeistungsArtAnzeigeName NOT IN ({_leistungsart_ignore})"),
        # Zuzahler: Rechnungsempfänger
        ("LTRIM(RTRIM(r.RechEmpfaenger)) NOT IN ('Mitarbeiter')", f"LTRIM(RTRIM(r.RechEmpfaenger)) NOT IN ({_zuzahler_empf})"),
        # Zuzahler: KostenÜbernahme
        ("ztn.KostenUebernahmeDurch = 'Arbeitgeber'", f"ztn.KostenUebernahmeDurch = '{_zuzahler_kostentyp}'"),
        # Dual-Studierende: Studienformat
        ("holy.Studienformat IN ('ausbildungsintegrierend', 'berufsintegrierend', 'berufsbegleitend +')", f"holy.Studienformat IN ({_dual_format})"),
        # Dual-Studierende: Bildungsabschnitt
        ("holy.Bildungsabschnitt = 'Erstausbildung'", f"holy.Bildungsabschnitt = '{_dual_bildung}'"),
    ]

    # Zeitraum-Parameter (müssen vorsichtig ersetzt werden)
    zeit_replacements = [
        ("YEAR(GETDATE())-2", f"YEAR(GETDATE())-{_jahre_stamm}"),
        ("YEAR(GETDATE()) - 2", f"YEAR(GETDATE()) - {_jahre_stamm}"),
        ("YEAR(DATEADD(YEAR, -5, GETDATE()))", f"YEAR(DATEADD(YEAR, -{_kohorten_j}, GETDATE()))"),
        ("YEAR(GETDATE()) - 4", f"YEAR(GETDATE()) - {_jahre_zuz}"),
    ]

    # Alle SQL-Variablen im Modul patchen
    sql_vars = [name for name in dir(module) if name.startswith('SQL_') or name.startswith('_ZUZAHLER')]
    for var_name in sql_vars:
        val = getattr(module, var_name)
        if not isinstance(val, str):
            continue
        for old, new in replacements:
            val = val.replace(old, new)
        for old, new in zeit_replacements:
            val = val.replace(old, new)
        setattr(module, var_name, val)

    print('[Queries] SQL-Strings mit DB-Konfiguration gepatcht')


# ─── Queries initialisieren ───
_build_sql_queries()
_patch_remaining_queries()


# ═══════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Benutzername und Passwort erforderlich'}), 400
    user_info = authenticate_user(username, password)
    if not user_info:
        return jsonify({'error': 'Anmeldung fehlgeschlagen oder keine Berechtigung'}), 401
    session.permanent = True
    session['user'] = user_info
    return jsonify({'ok': True, 'user': user_info})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/me')
def me():
    user = session.get('user')
    if not user:
        return jsonify({'authenticated': False}), 401
    return jsonify({'authenticated': True, 'user': user})


# ═══════════════════════════════════════
# USER MANAGEMENT (Admin-Panel) – DB-basiert
# ═══════════════════════════════════════

def _ldap_lookup(username):
    """Prüft ob ein Benutzer im AD existiert. Gibt display_name zurück oder None."""
    server = ldap3.Server(LDAP_SERVER, get_info=ldap3.DSA)
    conn = ldap3.Connection(server, authentication=ldap3.ANONYMOUS)
    try:
        conn.bind()
        search_filter = f'(&(objectClass=user)(sAMAccountName={ldap3.utils.conv.escape_filter_chars(username)}))'
        conn.search(LDAP_BASE_DN, search_filter, attributes=['displayName', 'mail'])
        if conn.entries:
            entry = conn.entries[0]
            return {
                'display_name': str(entry.displayName) if entry.displayName else _auto_display_name(username),
                'email': str(entry.mail) if entry.mail else ''
            }
        return None
    except Exception:
        return {'display_name': _auto_display_name(username), 'email': ''}
    finally:
        conn.unbind()


@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Gibt alle Berechtigungseinträge für diese App aus der DB zurück."""
    conn = _get_apps_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ID, Berechtigt, Recht, Typ, Aktiv "
                "FROM t_app_berechtigungen WHERE App = %s ORDER BY Recht, Berechtigt",
                (APP_NAME,)
            )
            rows = cur.fetchall()
        users = []
        for row_id, berechtigt, recht, typ, aktiv in rows:
            users.append({
                'id': row_id,
                'berechtigt': berechtigt,
                'display_name': _auto_display_name(berechtigt),
                'recht': recht,
                'typ': typ,
                'aktiv': bool(aktiv)
            })
        return jsonify({'ok': True, 'users': users})
    finally:
        conn.close()


@app.route('/api/users', methods=['POST'])
@admin_required
def add_user():
    """Fügt einen neuen Berechtigungseintrag hinzu (niedrigste Rolle: read).
    Prüft per LDAP ob der User/die Gruppe existiert."""
    data = request.get_json(silent=True) or {}
    berechtigt = data.get('username', '').strip()
    typ = data.get('typ', 'user').strip()
    if not berechtigt:
        return jsonify({'error': 'Name (Benutzer oder Gruppe) erforderlich'}), 400
    if typ not in ('user', 'gruppe'):
        return jsonify({'error': 'Typ muss "user" oder "gruppe" sein'}), 400

    # Bei Typ=user: LDAP-Prüfung
    if typ == 'user':
        ldap_info = _ldap_lookup(berechtigt)
        # ldap_info kann None sein wenn anonymer Bind fehlschlägt – trotzdem zulassen

    # Prüfen ob Eintrag bereits existiert
    conn = _get_apps_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ID FROM t_app_berechtigungen "
                "WHERE App = %s AND Berechtigt = %s AND Recht = 'read'",
                (APP_NAME, berechtigt)
            )
            if cur.fetchone():
                return jsonify({'error': 'Eintrag existiert bereits'}), 409

            cur.execute(
                "INSERT INTO t_app_berechtigungen (App, Berechtigt, Recht, Typ, Aktiv) "
                "VALUES (%s, %s, 'read', %s, 1)",
                (APP_NAME, berechtigt, typ)
            )
            conn.commit()
            new_id = cur.lastrowid
        return jsonify({'ok': True, 'user': {
            'id': new_id,
            'berechtigt': berechtigt,
            'display_name': _auto_display_name(berechtigt),
            'recht': 'read',
            'typ': typ,
            'aktiv': True
        }}), 201
    finally:
        conn.close()


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Ändert das Recht eines Berechtigungseintrags."""
    data = request.get_json(silent=True) or {}
    new_recht = data.get('recht', '').strip()
    if new_recht not in ('admin', 'write', 'read'):
        return jsonify({'error': 'Ungültiges Recht (admin, write, read)'}), 400

    conn = _get_apps_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE t_app_berechtigungen SET Recht = %s WHERE ID = %s AND App = %s",
                (new_recht, user_id, APP_NAME)
            )
            if cur.rowcount == 0:
                return jsonify({'error': 'Eintrag nicht gefunden'}), 404
            conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Deaktiviert einen Berechtigungseintrag. Admin kann sich nicht selbst entfernen."""
    conn = _get_apps_connection()
    try:
        with conn.cursor() as cur:
            # Prüfen wer gelöscht wird
            cur.execute(
                "SELECT Berechtigt, Typ FROM t_app_berechtigungen WHERE ID = %s AND App = %s",
                (user_id, APP_NAME)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Eintrag nicht gefunden'}), 404

            berechtigt, typ = row
            current_user = session.get('user', {}).get('username', '').lower()
            if typ == 'user' and berechtigt.lower() == current_user:
                return jsonify({'error': 'Sie können sich nicht selbst entfernen'}), 403

            cur.execute(
                "DELETE FROM t_app_berechtigungen WHERE ID = %s AND App = %s",
                (user_id, APP_NAME)
            )
            conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()


# ═══════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════

@app.route('/api/health')
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify(status='ok', database='connected')
    except Exception as e:
        return jsonify(status='error', database='disconnected', error=str(e)), 503


@app.route('/api/config/reload', methods=['POST'])
@admin_required
def reload_config_endpoint():
    """Lädt die Konfiguration aus MariaDB neu und baut SQL-Queries neu auf."""
    try:
        config_db.reload_config()
        _build_sql_queries()
        _patch_remaining_queries()
        CACHE.clear()
        return jsonify(success=True, message='Konfiguration neu geladen, Cache geleert')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/studiengaenge')
@login_required
def studiengaenge():
    try:
        cached = cache_get('studiengaenge')
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        rows = query_db(SQL_STUDIENGAENGE_LISTE)
        stud_rows = query_db(SQL_STUDIERENDE_AKTUELL)
        stud_map = {r['Produktkuerzel']: int(r['Gesamtstudierende']) for r in stud_rows}

        # ─── Zusammenfassungs-Logik (aus SG_Steckbrief_Generator.xlsm) ───
        PK_MAPPING = config_db.PK_MAPPING
        NAME_MAPPING = {
            'Business Administration - Healthcare Management': 'Business Administration',
            'Business Administration - dual kompakt': 'Business Administration',
            'Business Administration Vertiefung Public Management': 'Business Administration',
            'Business Administration, Vertiefung Public Management': 'Business Administration',
            'Business Administration - Public Management': 'Business Administration',
            'Business Administration – Versicherungsbetrieb': 'Business Administration',
            'Business Administration – Versicherungsvertrieb': 'Business Administration',
            'Engineering & Management': 'Wirtschaftsingenieurwesen',
            'Primärmedizinisches Versorgungs- und Praxismanagement': 'Primary Care Management',
            'Soziale Arbeit - kommunal': 'Soziale Arbeit',
            'Soziale Arbeit – kommunal': 'Soziale Arbeit',
            'Wirtschaftsinformatik – kommunal': 'Wirtschaftsinformatik',
            'Wirtschaftsinformatik - kommunal': 'Wirtschaftsinformatik',
        }

        # Studierende-Map auf zusammengefasste PKs umrechnen
        merged_stud = {}
        for pk, count in stud_map.items():
            merged_pk = PK_MAPPING.get(pk, pk)
            merged_stud[merged_pk] = merged_stud.get(merged_pk, 0) + count

        # Deduplizieren + Zusammenfassen: pro (zusammengefasstem) Produktkuerzel
        # Bei mehreren Varianten wird der kürzeste (generischste) Name verwendet
        sg_map = {}
        for r in rows:
            raw_pk = r['Produktkuerzel']
            pk = PK_MAPPING.get(raw_pk, raw_pk)
            # Studiengang-Name bereinigen: Kürzel aus Klammern extrahieren und Namen mappen
            sg_name = r['Studiengang'] or ''
            # Name ohne Kürzel extrahieren (z.B. "Pflege (BPF)" → "Pflege")
            import re
            name_match = re.match(r'^(.+?)\s*\([^)]+\)\s*$', sg_name)
            base_name = name_match.group(1).strip() if name_match else sg_name
            base_name = NAME_MAPPING.get(base_name, base_name)
            display_name = f'{base_name} ({pk})'

            # Kürzesten (generischsten) Namen bevorzugen
            if pk not in sg_map or len(display_name) < len(sg_map[pk]['Studiengang']):
                sg_map[pk] = {
                    'Produktkuerzel': pk,
                    'Studiengang': display_name,
                    'Hochschulbereich': r['Hochschulbereich'],
                    'HochschulbereichKuerzel': r['HochschulbereichKuerzel'],
                    'Abschluss': r.get('Abschluss') or ('Master' if pk.startswith('M') else 'Bachelor'),
                }

        # Studierende-Map aktualisieren
        stud_map = merged_stud

        # Nach HSB gruppieren
        hsb_map = {}

        for pk, r in sg_map.items():
            hsb_kuerzel = r['HochschulbereichKuerzel']
            if not hsb_kuerzel:
                continue
            if hsb_kuerzel not in hsb_map:
                hsb_cfg = config_db.HSB_CONFIG.get(hsb_kuerzel, {})
                hsb_map[hsb_kuerzel] = {
                    'id': hsb_kuerzel.lower().replace(' ', '_'),
                    'name': r['Hochschulbereich'],
                    'kuerzel': hsb_kuerzel,
                    'icon': hsb_cfg.get('icon', '📚'),
                    'farbe': hsb_cfg.get('farbe_hex', '#607D8B'),
                    'programmes': []
                }
            abschluss_raw = r.get('Abschluss') or ('Master' if pk.startswith('M') else 'Bachelor')
            abschluss_kurz = 'Master' if 'master' in abschluss_raw.lower() else 'Bachelor'
            hsb_map[hsb_kuerzel]['programmes'].append({
                'id': f'{hsb_kuerzel}_{abschluss_kurz[:1]}A_{pk}',
                'name': r['Studiengang'],
                'kurzname': pk,
                'abschluss': abschluss_raw,
                'studierende_gesamt': stud_map.get(pk, 0)
            })

        # Sortieren: Programme nach Name, HSBs nach Name
        for hsb in hsb_map.values():
            hsb['programmes'].sort(key=lambda p: p['name'])

        HSB_ORDER = config_db.HSB_ORDER
        data = sorted(hsb_map.values(), key=lambda h: HSB_ORDER.get(h['kuerzel'], 99))
        cache_set('studiengaenge', data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/trends')
@login_required
def trends(produktkuerzel):
    try:
        cache_key = f'trends_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        # Parameter wird 2x gebraucht im SQL (für SG-Filter in CASE WHEN)
        # expand_pk: alle Varianten (z.B. BBA → BBA,BBAb,BBAd,...) einbeziehen
        pk_variants = expand_pk(produktkuerzel)
        sql_zr, params_zr = pk_expand_sql(SQL_STUDIERENDE_ZEITREIHE, produktkuerzel)
        sql_hsz, params_hsz = pk_expand_sql(SQL_STUDIERENDE_HSZ, produktkuerzel)
        rows, hsz_rows, hsz_avg_rows = query_db_multi([
            (sql_zr, params_zr),
            (sql_hsz, params_hsz),
            (SQL_STUDIERENDE_HSZ_AVG, [])
        ])

        # Auf aktuelles Semester + letzte 6 begrenzen (=7 Semester)
        rows = _semester_filter_7(rows)
        hsz_rows = _semester_filter_7(hsz_rows)
        hsz_avg_rows = _semester_filter_7(hsz_avg_rows)

        # Nach Jahren gruppieren
        jahre = sorted(set(r['Jahr'] for r in rows), reverse=True)

        zeitreihe_ss, zeitreihe_ws = [], []
        fom_avg_ss, fom_avg_ws = [], []
        beginner_ss, beginner_ws = [], []
        beginner_fom_avg_ss, beginner_fom_avg_ws = [], []

        for jahr in jahre:
            ss = next((r for r in rows if r['Jahr'] == jahr and r['SemesterTyp'] == 'SS'), None)
            ws = next((r for r in rows if r['Jahr'] == jahr and r['SemesterTyp'] == 'WS'), None)

            zeitreihe_ss.append(int(ss['Gesamtstudierende_SG']) if ss else 0)
            zeitreihe_ws.append(int(ws['Gesamtstudierende_SG']) if ws else 0)
            fom_avg_ss.append(round(float(ss['Gesamtstudierende_FOM_Avg'])) if ss else 0)
            fom_avg_ws.append(round(float(ws['Gesamtstudierende_FOM_Avg'])) if ws else 0)
            beginner_ss.append(int(ss['Beginner_SG']) if ss else 0)
            beginner_ws.append(int(ws['Beginner_SG']) if ws else 0)
            beginner_fom_avg_ss.append(round(float(ss['Beginner_FOM_Avg'])) if ss else 0)
            beginner_fom_avg_ws.append(round(float(ws['Beginner_FOM_Avg'])) if ws else 0)

        # Aktuellster Wert + Delta (Vergleich: gleiches Semester-Typ Vorjahr)
        # Jahre sind absteigend sortiert: Index 0 = neuestes Jahr
        if zeitreihe_ws[0]:
            aktuell = zeitreihe_ws[0]
            vorher = zeitreihe_ws[1] if len(zeitreihe_ws) >= 2 else 0
        else:
            aktuell = zeitreihe_ss[0] if zeitreihe_ss else 0
            vorher = zeitreihe_ss[1] if len(zeitreihe_ss) >= 2 else 0
        diff = aktuell - vorher
        pct = f'{(diff / vorher * 100):.1f}'.replace('.', ',') if vorher else '0,0'
        delta_str = f'{"+" if diff >= 0 else ""}{diff} ({"+" if diff >= 0 else ""}{pct}%)'

        # Beginner aktuell + Delta (nur letzte verfügbare Semester vs. Vorjahr)
        # SS-Beginner aktuell vs. SS-Beginner Vorjahr
        b_ss_aktuell = beginner_ss[0] if beginner_ss else 0
        b_ss_vorher = beginner_ss[1] if len(beginner_ss) >= 2 else 0
        # WS-Beginner aktuell vs. WS-Beginner Vorjahr
        b_ws_aktuell = beginner_ws[0] if beginner_ws else 0
        b_ws_vorher = beginner_ws[1] if len(beginner_ws) >= 2 else 0
        # Nur Semester mit Daten für Delta nehmen
        if b_ws_aktuell:
            b_aktuell = b_ws_aktuell + b_ss_aktuell
            b_vorher = b_ws_vorher + b_ss_vorher
        else:
            b_aktuell = b_ss_aktuell
            b_vorher = b_ss_vorher
        b_diff = b_aktuell - b_vorher
        b_pct = f'{(b_diff / b_vorher * 100):.1f}'.replace('.', ',') if b_vorher else '0,0'
        b_delta = f'{"+" if b_diff >= 0 else ""}{b_diff} ({"+" if b_diff >= 0 else ""}{b_pct}%)'

        # HSZ-Daten aufbereiten
        hsz_data = {}
        for r in hsz_rows:
            hsz = r['Hochschulzentrum']
            jahr = r['Jahr']
            if hsz not in hsz_data:
                hsz_data[hsz] = {}
            if jahr not in hsz_data[hsz]:
                hsz_data[hsz][jahr] = {'ss': 0, 'ws': 0, 'beginner_ss': 0, 'beginner_ws': 0, 'avg_ss': 0, 'avg_ws': 0, 'avg_beginner_ss': 0, 'avg_beginner_ws': 0}
            if r['SemesterTyp'] == 'SS':
                hsz_data[hsz][jahr]['ss'] = int(r['Gesamtstudierende'])
                hsz_data[hsz][jahr]['beginner_ss'] = int(r['Beginner'])
            else:
                hsz_data[hsz][jahr]['ws'] = int(r['Gesamtstudierende'])
                hsz_data[hsz][jahr]['beginner_ws'] = int(r['Beginner'])

        # HSZ-Durchschnitt aller Studiengänge pro HSZ einfügen
        for r in hsz_avg_rows:
            hsz = r['Hochschulzentrum']
            jahr = r['Jahr']
            if hsz not in hsz_data:
                continue
            if jahr not in hsz_data[hsz]:
                continue
            if r['SemesterTyp'] == 'SS':
                hsz_data[hsz][jahr]['avg_ss'] = round(float(r['AvgStudierende'])) if r['AvgStudierende'] else 0
                hsz_data[hsz][jahr]['avg_beginner_ss'] = round(float(r['AvgBeginner'])) if r['AvgBeginner'] else 0
            else:
                hsz_data[hsz][jahr]['avg_ws'] = round(float(r['AvgStudierende'])) if r['AvgStudierende'] else 0
                hsz_data[hsz][jahr]['avg_beginner_ws'] = round(float(r['AvgBeginner'])) if r['AvgBeginner'] else 0

        data = {
            'studierende_gesamt': aktuell,
            'studierende_delta': delta_str,
            'studienbeginner': b_aktuell,
            'studienbeginner_delta': b_delta,
            'zeitreihe_semester': jahre,
            'zeitreihe_ss': zeitreihe_ss,
            'zeitreihe_ws': zeitreihe_ws,
            'zeitreihe_fom_avg_ss': fom_avg_ss,
            'zeitreihe_fom_avg_ws': fom_avg_ws,
            'studienbeginner_zeitreihe_semester': jahre,
            'studienbeginner_zeitreihe_ss': beginner_ss,
            'studienbeginner_zeitreihe_ws': beginner_ws,
            'studienbeginner_zeitreihe_fom_avg_ss': beginner_fom_avg_ss,
            'studienbeginner_zeitreihe_fom_avg_ws': beginner_fom_avg_ws,
            'hsz_detail': hsz_data
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/hszen')
@login_required
def aktive_hszen(produktkuerzel):
    try:
        cache_key = f'hszen_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)
        sql_hszen, params_hszen = pk_expand_sql(SQL_AKTIVE_HSZEN, produktkuerzel)
        rows = query_db(sql_hszen, params_hszen)
        data = [r['Hochschulzentrum'] for r in rows]
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ─── Cache leeren ───
@app.route('/api/cache/clear', methods=['POST'])
@admin_required
def clear_cache():
    CACHE.clear()
    return jsonify(success=True, message='Cache geleert')


@app.route('/api/cache/clear/<produktkuerzel>/<endpoint>', methods=['POST'])
@admin_required
def clear_cache_entry(produktkuerzel, endpoint):
    """Löscht einen einzelnen Cache-Eintrag für einen Studiengang/Endpoint."""
    key = f'{endpoint}_{produktkuerzel}'
    if key in CACHE:
        del CACHE[key]
    return jsonify(success=True, message=f'Cache-Eintrag {key} gelöscht')


@app.route('/api/cache/preload', methods=['POST'])
@admin_required
def preload_cache():
    """Lädt alle Daten für alle Studiengänge in den Cache (parallelisiert)."""
    import traceback
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Session-Daten für interne Requests merken
    _sess_data = {
        'username': session.get('username'),
        'role': session.get('role'),
        'display_name': session.get('display_name')
    }

    try:
        # 1) Studiengänge laden (füllt Cache)
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess.update(_sess_data)
            client.get('/api/studiengaenge')

        cached = cache_get('studiengaenge')
        if not cached:
            return jsonify(success=False, error='Studiengänge konnten nicht geladen werden'), 500

        # Alle Produktkuerzel sammeln
        all_pks = []
        for hsb in cached:
            for prog in hsb.get('programmes', []):
                all_pks.append(prog['kurzname'])

        base_endpoints = ['trends', 'hszen', 'anrechnungen', 'stammdaten', 'studienerfolg', 'zuzahler', 'rahmendaten', 'vertiefungsrichtungen']

        # Alle zu ladenden Aufgaben sammeln
        tasks = []
        for pk in all_pks:
            pk_endpoints = list(base_endpoints)
            if not pk.startswith('M'):
                pk_endpoints.append('uebergang')
            else:
                pk_endpoints.append('herkunft')
            for ep in pk_endpoints:
                tasks.append((pk, ep))

        loaded = 0
        errors = []

        def fetch_endpoint(pk, ep):
            """Einzelnen Endpoint laden (eigene DB-Connection pro Thread)."""
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    sess.update(_sess_data)
                resp = client.get(f'/api/steckbrief/{pk}/{ep}')
                return resp.status_code

        # Max 8 parallele Threads (je eigene DB-Connection)
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_map = {executor.submit(fetch_endpoint, pk, ep): (pk, ep) for pk, ep in tasks}
            for future in as_completed(future_map):
                pk, ep = future_map[future]
                try:
                    status = future.result()
                    if status == 200:
                        loaded += 1
                    else:
                        errors.append(f'{pk}/{ep}: HTTP {status}')
                except Exception as ex:
                    errors.append(f'{pk}/{ep}: {str(ex)}')

        return jsonify(success=True, studiengaenge=len(all_pks), endpoints_loaded=loaded,
                       errors=errors[:10] if errors else [])
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500

# ─── Debug: Semesterkuerzel-Format prüfen ───
@app.route('/api/debug/semester-format')
@login_required
def debug_semester():
    try:
        rows = query_db("""
            SELECT DISTINCT TOP 20 Semesterkuerzel
            FROM BCW_DWH.dwh.C_Studierendenzahlen
            ORDER BY Semesterkuerzel DESC
        """)
        return jsonify(success=True, data=rows)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ─── Debug: Verfügbare Produktkuerzel ───
@app.route('/api/debug/produktkuerzel')
@login_required
def debug_produktkuerzel():
    try:
        rows = query_db("""
            SELECT DISTINCT TOP 50 Produktkuerzel, Studiengang, Hochschulbereich
            FROM BCW_DWH.dwh.C_Studierendenzahlen
            WHERE Institut = 'FOM'
            ORDER BY Produktkuerzel
        """)
        return jsonify(success=True, data=rows)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/anrechnungen')
@login_required
def anrechnungen(produktkuerzel):
    try:
        cache_key = f'anrechnungen_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        # Optimiert: 2-Temp-Tabelle Ansatz – Cross-DB Join nur einmal
        variants = expand_pk(produktkuerzel)
        pk_placeholders = ','.join('?' * len(variants))

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # 1) #anr_data: ERST NV prüfen – wer hat eine Anrechnung? (PK-gefiltert, ohne Population)
            try: cursor.execute("DROP TABLE IF EXISTS #anr_data")
            except Exception: pass
            cursor.execute("CREATE TABLE #anr_data (StudienEintragID INT, PersonenFID INT, Fach NVARCHAR(200), ModulFID INT, AnerkanntText NVARCHAR(500), HSZ NVARCHAR(100))")
            cursor.execute(f"""
                INSERT INTO #anr_data
                SELECT DISTINCT se.StudienEintragID, se.PersonenFID, n.Fach, n.ModulFID, pe.AnerkanntText, l.Hochschulzentrum
                FROM BCW_DWH.dwh.Noten n
                INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = n.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
                INNER JOIN BCW_STA.mariadb.t_pruefungsergebnisse pe ON pe.PruefungsErgebnisID = n.PruefungsErgebnisFID
                INNER JOIN BCW_STA.mariadb.t_notencache nc ON nc.PruefungsergebnisFID = pe.PruefungsErgebnisID
                WHERE pe.Anerkannt NOT IN ('N', 'Z')
                  AND nc.AnerkanntFach = 1
                  AND l.Institut = 'FOM'
                  AND p.Testperson = 0
                  AND l.Ausrichtung = 'national'
                  AND l.Produktkuerzel IN ({pk_placeholders})
            """, variants)

            # 2) #gs_anr: Population (Beginner/Quereinsteiger mit UV) – für Total + "Keine"
            #    Kein Zustand-Filter (Zustand=1 ist nur aktueller Snapshot)
            try: cursor.execute("DROP TABLE IF EXISTS #gs_anr")
            except Exception: pass
            cursor.execute("CREATE TABLE #gs_anr (StudienEintragID INT, PersonenFID INT, HSZ NVARCHAR(100))")
            cursor.execute(f"""
                INSERT INTO #gs_anr
                SELECT DISTINCT se.StudienEintragID, se.PersonenFID, l.Hochschulzentrum
                FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
                INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
                INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
                WHERE l.Institut = 'FOM'
                  AND p.Testperson = 0
                  AND sg.StatusGruppe = 'Beginner mit UV'
                  AND sz.Semesterkuerzel >= CASE
                      WHEN MONTH(GETDATE()) >= 9 THEN CONCAT(YEAR(GETDATE())-2, '-SS')
                      WHEN MONTH(GETDATE()) >= 3 THEN CONCAT(YEAR(GETDATE())-3, '-WS')
                      ELSE CONCAT(YEAR(GETDATE())-3, '-SS')
                  END
                  AND sz.Semesterkuerzel <= CASE
                      WHEN MONTH(GETDATE()) >= 9 THEN CONCAT(YEAR(GETDATE()), '-WS')
                      WHEN MONTH(GETDATE()) >= 3 THEN CONCAT(YEAR(GETDATE()), '-SS')
                      ELSE CONCAT(YEAR(GETDATE())-1, '-WS')
                  END
                  AND se.ImmatrikulationsDatum IS NOT NULL
                  AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
                  AND l.Ausrichtung = 'national'
                  AND l.Produktkuerzel IN ({pk_placeholders})
            """, variants)

            # 3) #antrag_qual: Qualifikation aus Anträgen für Personen MIT Anrechnung
            try: cursor.execute("DROP TABLE IF EXISTS #antrag_qual")
            except Exception: pass
            cursor.execute("CREATE TABLE #antrag_qual (PersonenFID INT, Qualifikation NVARCHAR(100))")
            cursor.execute(f"""
                INSERT INTO #antrag_qual
                SELECT sub.PersonenFID,
                    CASE
                        WHEN MAX(CASE WHEN lart.LeistungsArtAnzeigeName LIKE '%Hochschulische Leistung%' THEN 1 ELSE 0 END) = 1
                             AND MAX(CASE WHEN lart.LeistungsArtAnzeigeName LIKE '%Ausbildung%'
                                          OR lart.LeistungsArtAnzeigeName LIKE '%Ausserhochschulische Leistung%' THEN 1 ELSE 0 END) = 1
                        THEN 'Hochschulisch und Beruflich'
                        WHEN MAX(CASE WHEN lart.LeistungsArtAnzeigeName LIKE '%Hochschulische Leistung%' THEN 1 ELSE 0 END) = 1
                        THEN 'Hochschulisch'
                        ELSE 'Beruflich'
                    END AS Qualifikation
                FROM (SELECT DISTINCT PersonenFID FROM #anr_data) sub
                INNER JOIN BCW_STA.mariadb.Antraege a ON a.PersonenFID = sub.PersonenFID
                INNER JOIN (
                    SELECT al.AntragFiD, STRING_AGG(la.LeistungsArtAnzeigeName, ', ') AS LeistungsArtAnzeigeName
                    FROM BCW_STA.mariadb.AntragLeistungsart al
                    LEFT JOIN BCW_STA.mariadb.Leistungsart la ON al.LeistungsartFId = la.Id
                    WHERE la.LeistungsArtAnzeigeName NOT IN ('Einschreibehindernispruefung', 'Kooperation')
                    GROUP BY al.AntragFiD
                ) lart ON a.ID = lart.AntragFiD
                INNER JOIN BCW_STA.mariadb.Ergebnisse e ON e.AnrechnungenFid = a.Id
                LEFT JOIN BCW_DWH.dwh.Lehrgaenge l2 ON e.VerwaltungsPruefungsordnungFid = l2.POID
                    AND l2.Hochschulbereich IS NOT NULL
                WHERE l2.Produktkuerzel IN ({pk_placeholders})
                GROUP BY sub.PersonenFID
            """, variants)

            # 4) Stats: StudienEintraege mit Anrechnung klassifizieren (Anträge primär, AnerkanntText Fallback)
            #    3-Wege: HS, BER, HS+BER – NUR Einträge die auch in der Population (#gs_anr) sind
            cursor.execute("""
                WITH
                antrag_eintraege AS (
                    SELECT g.StudienEintragID,
                        CASE WHEN aq.Qualifikation = 'Hochschulisch' THEN 1
                             WHEN aq.Qualifikation = 'Hochschulisch und Beruflich' THEN 1 ELSE 0 END AS hat_hs,
                        CASE WHEN aq.Qualifikation = 'Beruflich' THEN 1
                             WHEN aq.Qualifikation = 'Hochschulisch und Beruflich' THEN 1 ELSE 0 END AS hat_ber
                    FROM #antrag_qual aq
                    INNER JOIN #gs_anr g ON g.PersonenFID = aq.PersonenFID
                ),
                kommentar_eintraege AS (
                    SELECT g.StudienEintragID,
                        MAX(CASE WHEN d.AnerkanntText LIKE '%HS%' OR d.AnerkanntText LIKE '%Auslandsstudium%'
                                      OR d.AnerkanntText LIKE '%ERASMUS%' THEN 1 ELSE 0 END) AS hat_hs,
                        MAX(CASE WHEN d.AnerkanntText NOT LIKE '%HS%' AND d.AnerkanntText NOT LIKE '%Auslandsstudium%'
                                      AND d.AnerkanntText NOT LIKE '%ERASMUS%' THEN 1 ELSE 0 END) AS hat_ber
                    FROM #anr_data d
                    INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                    WHERE d.PersonenFID NOT IN (SELECT PersonenFID FROM #antrag_qual)
                    GROUP BY g.StudienEintragID
                ),
                alle_anr AS (
                    SELECT StudienEintragID, hat_hs, hat_ber FROM antrag_eintraege
                    UNION ALL
                    SELECT StudienEintragID, hat_hs, hat_ber FROM kommentar_eintraege
                )
                SELECT
                    COUNT(DISTINCT CASE WHEN hat_hs = 1 AND hat_ber = 0 THEN StudienEintragID END) AS Hochschulisch,
                    COUNT(DISTINCT CASE WHEN hat_ber = 1 AND hat_hs = 0 THEN StudienEintragID END) AS Beruflich,
                    COUNT(DISTINCT CASE WHEN hat_hs = 1 AND hat_ber = 1 THEN StudienEintragID END) AS HsBer,
                    (SELECT COUNT(DISTINCT StudienEintragID) FROM #gs_anr
                     WHERE StudienEintragID NOT IN (SELECT DISTINCT StudienEintragID FROM #anr_data)) AS Keine,
                    (SELECT COUNT(DISTINCT StudienEintragID) FROM #gs_anr) AS Total
                FROM alle_anr
            """)
            columns = [col[0] for col in cursor.description]
            s = dict(zip(columns, cursor.fetchone()))

            # 4b) Gleiche Stats pro HSZ
            cursor.execute("""
                WITH
                antrag_eintraege AS (
                    SELECT g.StudienEintragID, g.HSZ,
                        CASE WHEN aq.Qualifikation = 'Hochschulisch' THEN 1
                             WHEN aq.Qualifikation = 'Hochschulisch und Beruflich' THEN 1 ELSE 0 END AS hat_hs,
                        CASE WHEN aq.Qualifikation = 'Beruflich' THEN 1
                             WHEN aq.Qualifikation = 'Hochschulisch und Beruflich' THEN 1 ELSE 0 END AS hat_ber
                    FROM #antrag_qual aq
                    INNER JOIN #gs_anr g ON g.PersonenFID = aq.PersonenFID
                ),
                kommentar_eintraege AS (
                    SELECT g.StudienEintragID, g.HSZ,
                        MAX(CASE WHEN d.AnerkanntText LIKE '%HS%' OR d.AnerkanntText LIKE '%Auslandsstudium%'
                                      OR d.AnerkanntText LIKE '%ERASMUS%' THEN 1 ELSE 0 END) AS hat_hs,
                        MAX(CASE WHEN d.AnerkanntText NOT LIKE '%HS%' AND d.AnerkanntText NOT LIKE '%Auslandsstudium%'
                                      AND d.AnerkanntText NOT LIKE '%ERASMUS%' THEN 1 ELSE 0 END) AS hat_ber
                    FROM #anr_data d
                    INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                    WHERE d.PersonenFID NOT IN (SELECT PersonenFID FROM #antrag_qual)
                    GROUP BY g.StudienEintragID, g.HSZ
                ),
                alle_anr AS (
                    SELECT StudienEintragID, HSZ, hat_hs, hat_ber FROM antrag_eintraege
                    UNION ALL
                    SELECT StudienEintragID, HSZ, hat_hs, hat_ber FROM kommentar_eintraege
                )
                SELECT
                    ISNULL(sub.HSZ, gs_t.HSZ) AS HSZ,
                    ISNULL(sub.Hochschulisch, 0) AS Hochschulisch,
                    ISNULL(sub.Beruflich, 0) AS Beruflich,
                    ISNULL(sub.HsBer, 0) AS HsBer,
                    ISNULL(gs_t.Total, 0) - ISNULL(sub.Hochschulisch, 0) - ISNULL(sub.Beruflich, 0) - ISNULL(sub.HsBer, 0) AS Keine,
                    ISNULL(gs_t.Total, 0) AS Total
                FROM (
                    SELECT HSZ,
                        COUNT(DISTINCT CASE WHEN hat_hs = 1 AND hat_ber = 0 THEN StudienEintragID END) AS Hochschulisch,
                        COUNT(DISTINCT CASE WHEN hat_ber = 1 AND hat_hs = 0 THEN StudienEintragID END) AS Beruflich,
                        COUNT(DISTINCT CASE WHEN hat_hs = 1 AND hat_ber = 1 THEN StudienEintragID END) AS HsBer
                    FROM alle_anr
                    GROUP BY HSZ
                ) sub
                FULL OUTER JOIN (
                    SELECT HSZ, COUNT(DISTINCT StudienEintragID) AS Total
                    FROM #gs_anr
                    GROUP BY HSZ
                ) gs_t ON sub.HSZ = gs_t.HSZ
            """)
            hsz_cols = [col[0] for col in cursor.description]
            hsz_stats = {}
            for row in cursor.fetchall():
                r = dict(zip(hsz_cols, row))
                hsz_name = r['HSZ']
                if hsz_name:
                    t = max(int(r['Total'] or 0), 1)
                    h = int(r['Hochschulisch'] or 0)
                    b = int(r['Beruflich'] or 0)
                    hb = int(r['HsBer'] or 0)
                    k = int(r['Keine'] or 0)
                    hsz_stats[hsz_name] = {
                        'hochschulisch_abs': h, 'hochschulisch_pct': round(h / t * 100, 1),
                        'beruflich_abs': b, 'beruflich_pct': round(b / t * 100, 1),
                        'hs_ber_abs': hb, 'hs_ber_pct': round(hb / t * 100, 1),
                        'keine_abs': k, 'keine_pct': round(k / t * 100, 1)
                    }

            # 5) Top Module – alle, nur HS, nur BER, HS+BER
            cursor.execute("""
                SELECT TOP 10 MIN(d.Fach) AS Name, COUNT(DISTINCT d.StudienEintragID) AS Cnt
                FROM #anr_data d
                INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                GROUP BY d.ModulFID ORDER BY Cnt DESC
            """)
            top_module = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            # Top Module – nur Hochschulisch (rein HS, ohne Kombi)
            cursor.execute("""
                WITH person_hs AS (
                    SELECT PersonenFID FROM #antrag_qual WHERE Qualifikation = 'Hochschulisch'
                    UNION
                    SELECT d.PersonenFID FROM #anr_data d
                    WHERE d.PersonenFID NOT IN (SELECT PersonenFID FROM #antrag_qual)
                    GROUP BY d.PersonenFID
                    HAVING MAX(CASE WHEN d.AnerkanntText LIKE '%HS%' OR d.AnerkanntText LIKE '%Auslandsstudium%'
                                    OR d.AnerkanntText LIKE '%ERASMUS%' THEN 1 ELSE 0 END) = 1
                       AND MAX(CASE WHEN d.AnerkanntText NOT LIKE '%HS%' AND d.AnerkanntText NOT LIKE '%Auslandsstudium%'
                                    AND d.AnerkanntText NOT LIKE '%ERASMUS%' THEN 1 ELSE 0 END) = 0
                )
                SELECT TOP 10 MIN(d.Fach) AS Name, COUNT(DISTINCT d.StudienEintragID) AS Cnt
                FROM #anr_data d
                INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                INNER JOIN person_hs ph ON ph.PersonenFID = d.PersonenFID
                GROUP BY d.ModulFID ORDER BY Cnt DESC
            """)
            top_module_hs = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            # Top Module – nur Beruflich (rein BER, ohne Kombi)
            cursor.execute("""
                WITH person_ber AS (
                    SELECT PersonenFID FROM #antrag_qual WHERE Qualifikation = 'Beruflich'
                    UNION
                    SELECT d.PersonenFID FROM #anr_data d
                    WHERE d.PersonenFID NOT IN (SELECT PersonenFID FROM #antrag_qual)
                    GROUP BY d.PersonenFID
                    HAVING MAX(CASE WHEN d.AnerkanntText LIKE '%HS%' OR d.AnerkanntText LIKE '%Auslandsstudium%'
                                    OR d.AnerkanntText LIKE '%ERASMUS%' THEN 1 ELSE 0 END) = 0
                )
                SELECT TOP 10 MIN(d.Fach) AS Name, COUNT(DISTINCT d.StudienEintragID) AS Cnt
                FROM #anr_data d
                INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                INNER JOIN person_ber pb ON pb.PersonenFID = d.PersonenFID
                GROUP BY d.ModulFID ORDER BY Cnt DESC
            """)
            top_module_ber = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            # Top Module – Hochschulisch UND Beruflich (Kombi)
            cursor.execute("""
                WITH person_both AS (
                    SELECT PersonenFID FROM #antrag_qual WHERE Qualifikation = 'Hochschulisch und Beruflich'
                    UNION
                    SELECT d.PersonenFID FROM #anr_data d
                    WHERE d.PersonenFID NOT IN (SELECT PersonenFID FROM #antrag_qual)
                    GROUP BY d.PersonenFID
                    HAVING MAX(CASE WHEN d.AnerkanntText LIKE '%HS%' OR d.AnerkanntText LIKE '%Auslandsstudium%'
                                    OR d.AnerkanntText LIKE '%ERASMUS%' THEN 1 ELSE 0 END) = 1
                       AND MAX(CASE WHEN d.AnerkanntText NOT LIKE '%HS%' AND d.AnerkanntText NOT LIKE '%Auslandsstudium%'
                                    AND d.AnerkanntText NOT LIKE '%ERASMUS%' THEN 1 ELSE 0 END) = 1
                )
                SELECT TOP 10 MIN(d.Fach) AS Name, COUNT(DISTINCT d.StudienEintragID) AS Cnt
                FROM #anr_data d
                INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                INNER JOIN person_both pb ON pb.PersonenFID = d.PersonenFID
                GROUP BY d.ModulFID ORDER BY Cnt DESC
            """)
            top_module_both = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            # 5b) Top Module per HSZ
            cursor.execute("""
                SELECT g.HSZ, MIN(d.Fach) AS Name, d.ModulFID, COUNT(DISTINCT d.StudienEintragID) AS Cnt
                FROM #anr_data d
                INNER JOIN #gs_anr g ON g.StudienEintragID = d.StudienEintragID
                GROUP BY g.HSZ, d.ModulFID
            """)
            top_module_hsz_raw = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            # Aufräumen
            try: cursor.execute("DROP TABLE IF EXISTS #gs_anr; DROP TABLE IF EXISTS #anr_data; DROP TABLE IF EXISTS #antrag_qual")
            except Exception: pass

            print(f"[Anrechnungen] {produktkuerzel}: Anträge-Logik (Fallback: Kommentar/AnerkanntText)")
        except Exception:
            try: conn.close()
            except Exception: pass
            raise
        else:
            release_connection(conn)

        total = max(int(s.get('Total', 0)), 1)
        hs = int(s.get('Hochschulisch', 0))
        ber = int(s.get('Beruflich', 0))
        hs_ber = int(s.get('HsBer', 0))
        keine = int(s.get('Keine', 0))

        # Per-HSZ Top Module aufbereiten und in hsz_stats einfügen
        hsz_top_module_map = {}
        for r in top_module_hsz_raw:
            hsz_name = r.get('HSZ')
            if hsz_name:
                hsz_top_module_map.setdefault(hsz_name, []).append({'name': r['Name'], 'count': int(r['Cnt'])})
        for hsz_name, modules in hsz_top_module_map.items():
            modules.sort(key=lambda x: x['count'], reverse=True)
            top10_modules = modules[:10]
            if hsz_name in hsz_stats:
                hsz_stats[hsz_name]['top_module'] = top10_modules

        data = {
            'hochschulisch_abs': hs,
            'hochschulisch_pct': round(hs / total * 100, 1),
            'beruflich_abs': ber,
            'beruflich_pct': round(ber / total * 100, 1),
            'hs_ber_abs': hs_ber,
            'hs_ber_pct': round(hs_ber / total * 100, 1),
            'keine_abs': keine,
            'keine_pct': round(keine / total * 100, 1),
            'quelle': 'antraege',
            'top_module': [{'name': r['Name'], 'count': int(r['Cnt'])} for r in top_module],
            'top_module_hs': [{'name': r['Name'], 'count': int(r['Cnt'])} for r in top_module_hs],
            'top_module_ber': [{'name': r['Name'], 'count': int(r['Cnt'])} for r in top_module_ber],
            'top_module_both': [{'name': r['Name'], 'count': int(r['Cnt'])} for r in top_module_both],
            'hsz_detail': hsz_stats
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/stammdaten')
@login_required
def stammdaten(produktkuerzel):
    try:
        cache_key = f'stammdaten_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        sql_alter, p_alter = pk_expand_sql(SQL_STAMMDATEN_ALTER, produktkuerzel)
        sql_detail, p_detail = pk_expand_sql(SQL_STAMMDATEN_DETAIL, produktkuerzel)
        sql_beruf_a, p_beruf_a = pk_expand_sql(SQL_STAMMDATEN_BERUFSAUSBILDUNG, produktkuerzel)
        alter_rows, detail_rows, beruf_rows = query_db_multi([
            (sql_alter, p_alter),
            (sql_detail, p_detail),
            (sql_beruf_a, p_beruf_a)
        ])

        def fmt_sem(sk):
            return f"{'WS' if sk.endswith('WS') else 'SS'}-{sk[:4]}"

        def pct(val, total):
            return round(int(val or 0) / max(int(total or 0), 1) * 100, 1)

        def detail_block(r):
            if not r:
                return {'weiblich': 0, 'maennlich': 0}, {'inlaendisch': 0, 'auslaendisch': 0, 'dueh': 0}, {'dual': 0, 'tagesstudium': 0, 'nein': 0}, {'ja': 0, 'nein': 0}
            t = int(r['Total'] or 1)
            geschlecht = {'weiblich': pct(r['Weiblich'], t), 'maennlich': pct(r['Maennlich'], t)}
            inl = int(r.get('Inlaendisch', 0) or 0)
            ausl = int(r.get('Auslaendisch', 0) or 0)
            unbek = int(r.get('Unbekannt', 0) or 0)
            staatsang = {'inlaendisch': pct(inl, t), 'auslaendisch': pct(ausl, t), 'dueh': pct(unbek, t)}
            dual_v = int(r.get('Dual', 0) or 0)
            tages = int(r.get('Tagesstudium', 0) or 0)
            dual = {'dual': pct(dual_v, t), 'tagesstudium': pct(tages, t), 'nein': pct(t - dual_v - tages, t)}
            offene_v = int(r.get('OffeneHochschule', 0) or 0)
            intern = {'ja': pct(offene_v, t), 'nein': pct(t - offene_v, t)}
            return geschlecht, staatsang, dual, intern

        def sum_detail_rows(rows_list):
            """Sum detail rows into aggregated row."""
            if not rows_list:
                return None
            agg = {'Total': 0, 'Weiblich': 0, 'Maennlich': 0, 'Inlaendisch': 0, 'Auslaendisch': 0,
                   'Unbekannt': 0, 'Dual': 0, 'Tagesstudium': 0, 'OffeneHochschule': 0}
            for r in rows_list:
                for k in agg:
                    agg[k] += int(r.get(k, 0) or 0)
            return agg

        # ─── Overall (alle HSZ aggregiert) ───
        # Alter: weighted average per semester
        sem_alter = {}
        for r in alter_rows:
            sk = r['Semesterkuerzel']
            avg_val = float(r['DurchschnittsAlter']) if r['DurchschnittsAlter'] else None
            cnt = int(r['Cnt'] or 0)
            if avg_val is not None and cnt > 0:
                if sk not in sem_alter:
                    sem_alter[sk] = {'sum': 0, 'cnt': 0}
                sem_alter[sk]['sum'] += avg_val * cnt
                sem_alter[sk]['cnt'] += cnt
        alter_overall = [{'Semesterkuerzel': sk, 'DurchschnittsAlter': d['sum'] / d['cnt']}
                         for sk, d in sorted(sem_alter.items()) if d['cnt'] > 0]
        alter_rows_filtered = _semester_filter_7(alter_overall)
        alter_semester = [fmt_sem(r['Semesterkuerzel']) for r in alter_rows_filtered]
        alter_werte = [round(float(r['DurchschnittsAlter']), 1) for r in alter_rows_filtered]

        # Detail: sum across HSZ per Zeitraum
        aktuell = sum_detail_rows([r for r in detail_rows if r['Zeitraum'] == 'aktuell'])
        rest = sum_detail_rows([r for r in detail_rows if r['Zeitraum'] == 'rest'])
        g_akt, s_akt, d_akt, i_akt = detail_block(aktuell)
        g_rest, s_rest, d_rest, i_rest = detail_block(rest)

        # Berufsausbildungen: aggregate across HSZ
        beruf_agg = {}
        for r in beruf_rows:
            key = (r['Zeitraum'], r['Berufsausbildung'])
            beruf_agg[key] = beruf_agg.get(key, 0) + int(r['Cnt'])
        beruf_akt = sorted([(ba, cnt) for (z, ba), cnt in beruf_agg.items() if z == 'aktuell'], key=lambda x: -x[1])
        beruf_rest = sorted([(ba, cnt) for (z, ba), cnt in beruf_agg.items() if z == 'rest'], key=lambda x: -x[1])
        total_akt = sum(cnt for _, cnt in beruf_akt) or 1
        total_rest = sum(cnt for _, cnt in beruf_rest) or 1

        # ─── Per-HSZ ───
        hsz_set_s = sorted(set(r.get('HSZ') for r in alter_rows if r.get('HSZ')) |
                           set(r.get('HSZ') for r in detail_rows if r.get('HSZ')))
        hsz_detail = {}
        for hsz in hsz_set_s:
            # Alter per HSZ
            h_alter = [r for r in alter_rows if r.get('HSZ') == hsz]
            h_alter_filtered = _semester_filter_7(h_alter)
            h_alter_semester = [fmt_sem(r['Semesterkuerzel']) for r in h_alter_filtered]
            h_alter_werte = [round(float(r['DurchschnittsAlter']), 1) if r['DurchschnittsAlter'] else None for r in h_alter_filtered]
            # Detail per HSZ
            h_aktuell = sum_detail_rows([r for r in detail_rows if r['Zeitraum'] == 'aktuell' and r.get('HSZ') == hsz])
            h_rest = sum_detail_rows([r for r in detail_rows if r['Zeitraum'] == 'rest' and r.get('HSZ') == hsz])
            h_g_akt, h_s_akt, h_d_akt, h_i_akt = detail_block(h_aktuell)
            h_g_rest, h_s_rest, h_d_rest, h_i_rest = detail_block(h_rest)
            # Beruf per HSZ
            h_beruf_akt = sorted([(r['Berufsausbildung'], int(r['Cnt'])) for r in beruf_rows if r['Zeitraum'] == 'aktuell' and r.get('HSZ') == hsz], key=lambda x: -x[1])
            h_beruf_rest = sorted([(r['Berufsausbildung'], int(r['Cnt'])) for r in beruf_rows if r['Zeitraum'] == 'rest' and r.get('HSZ') == hsz], key=lambda x: -x[1])
            h_total_akt = sum(cnt for _, cnt in h_beruf_akt) or 1
            h_total_rest = sum(cnt for _, cnt in h_beruf_rest) or 1
            hsz_detail[hsz] = {
                'alter_zeitreihe_semester': h_alter_semester,
                'alter_zeitreihe': h_alter_werte,
                'top_berufsausbildungen_aktuell': [{'name': ba, 'pct': round(cnt / h_total_akt * 100, 1)} for ba, cnt in h_beruf_akt[:5]],
                'top_berufsausbildungen_rest': [{'name': ba, 'pct': round(cnt / h_total_rest * 100, 1)} for ba, cnt in h_beruf_rest[:5]],
                'geschlecht_aktuell': h_g_akt, 'geschlecht_rest': h_g_rest,
                'staatsang_aktuell': h_s_akt, 'staatsang_rest': h_s_rest,
                'dual_aktuell': h_d_akt, 'dual_rest': h_d_rest,
                'intern_aktuell': h_i_akt, 'intern_rest': h_i_rest
            }

        data = {
            'alter_zeitreihe_semester': alter_semester,
            'alter_zeitreihe': alter_werte,
            'top_berufsausbildungen_aktuell': [{'name': ba, 'pct': round(cnt / total_akt * 100, 1)} for ba, cnt in beruf_akt[:5]],
            'top_berufsausbildungen_rest': [{'name': ba, 'pct': round(cnt / total_rest * 100, 1)} for ba, cnt in beruf_rest[:5]],
            'geschlecht_aktuell': g_akt,
            'geschlecht_rest': g_rest,
            'staatsang_aktuell': s_akt,
            'staatsang_rest': s_rest,
            'dual_aktuell': d_akt,
            'dual_rest': d_rest,
            'intern_aktuell': i_akt,
            'intern_rest': i_rest,
            'hsz_detail': hsz_detail
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/studienerfolg')
@login_required
def studienerfolg(produktkuerzel):
    try:
        cache_key = f'studienerfolg_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        # FOM-weite Queries global cachen (identisch für alle SG)
        fs_fom = cache_get('_global_fachsemester_fom')
        if not fs_fom:
            fs_fom = query_db(SQL_FACHSEMESTER_FOM)
            cache_set('_global_fachsemester_fom', fs_fom)
        vl_fom = cache_get('_global_verlaengerung_fom')
        if not vl_fom:
            vl_fom = query_db(SQL_VERLAENGERUNG_FOM)
            cache_set('_global_verlaengerung_fom', vl_fom)

        sql_fs, p_fs = pk_expand_sql(SQL_FACHSEMESTER, produktkuerzel)
        sql_vl, p_vl = pk_expand_sql(SQL_VERLAENGERUNG, produktkuerzel)
        fs_sg, vl_sg = query_db_multi([
            (sql_fs, p_fs),
            (sql_vl, p_vl)
        ])

        # Fachsemester: pivot to labels
        fs_labels_num = sorted(set(r['Fachsem'] for r in fs_sg if r['Fachsem'] not in ('0',)),
                               key=lambda x: 99 if x == '9+' else int(x))
        # Add special categories
        fs_labels = [f"{l}. FS" if l != '9+' else '9+' for l in fs_labels_num]
        fs_labels += ['Abbrecher', 'Wechsler', 'aktiv\n(regulär)', 'aktiv\n(Verlängerung)', 'Absolventen']

        def calc_fachsem_pct(rows, labels_num):
            # Pivot: fs -> cluster -> rsz -> count
            pivot = {}
            for r in rows:
                fs = r['Fachsem']
                if fs == '0':
                    continue
                cluster = r['AusstiegsCluster']
                if cluster is None:
                    continue
                rsz = int(r['RSZ'])
                pivot.setdefault(fs, {}).setdefault(cluster, {})
                pivot[fs][cluster][rsz] = pivot[fs][cluster].get(rsz, 0) + int(r['Anzahl'])

            kohortengroesse = sum(
                sum(sum(rv.values()) for rv in cv.values())
                for cv in pivot.values()
            ) or 1

            def cluster_total(name, rsz_filter=None):
                t = 0
                for l in labels_num:
                    cd = pivot.get(l, {}).get(name, {})
                    t += cd.get(rsz_filter, 0) if rsz_filter is not None else sum(cd.values())
                return t

            result = []
            for l in labels_num:
                abbrecher_fs = sum(pivot.get(l, {}).get('Abbrecher', {}).values())
                result.append(round(abbrecher_fs / kohortengroesse * 100, 1))

            # Summary: Abbrecher, Wechsler, aktiv (regulär), aktiv (Verlängerung), Absolventen
            result.append(round(cluster_total('Abbrecher') / kohortengroesse * 100, 1))
            result.append(round(cluster_total('Wechsler') / kohortengroesse * 100, 1))
            result.append(round(cluster_total('Eingeschrieben', 0) / kohortengroesse * 100, 1))
            result.append(round(cluster_total('Eingeschrieben', 1) / kohortengroesse * 100, 1))
            result.append(round(cluster_total('Absolvent') / kohortengroesse * 100, 1))
            return result

        # Aggregate fs_sg across HSZ for overall
        fs_sg_agg = {}
        for r in fs_sg:
            key = (r['Fachsem'], r['AusstiegsCluster'], int(r['RSZ']))
            fs_sg_agg[key] = fs_sg_agg.get(key, 0) + int(r['Anzahl'])
        fs_sg_overall = [{'Fachsem': k[0], 'AusstiegsCluster': k[1], 'RSZ': k[2], 'Anzahl': v} for k, v in fs_sg_agg.items()]

        sg_pcts = calc_fachsem_pct(fs_sg_overall, fs_labels_num)
        fom_pcts = calc_fachsem_pct(fs_fom, fs_labels_num)

        # Verlängerungssemester (nur Absolventen, Clustering: > 8 → '9+', < 0 → '0')
        # Berechnung: ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4)
        def calc_verlaengerung(rows):
            pivot = {}
            for r in rows:
                sv = int(r['VerlaengerungsSem'])
                if sv < 0:
                    sv = 0
                if sv > 8:
                    key = '9+'
                else:
                    key = str(sv)
                pivot[key] = pivot.get(key, 0) + int(r['Anzahl'])
            return pivot

        # Aggregate vl_sg across HSZ for overall
        vl_sg_agg = {}
        for r in vl_sg:
            sv = int(r['VerlaengerungsSem'])
            if sv < 0:
                sv = 0
            if sv > 8:
                key = '9+'
            else:
                key = str(sv)
            vl_sg_agg[key] = vl_sg_agg.get(key, 0) + int(r['Anzahl'])
        vl_sg_pivot = vl_sg_agg
        vl_fom_pivot = calc_verlaengerung(vl_fom)
        # Sortierung: '0', '1', ..., '8', '9+'
        sort_key = lambda x: 99 if x == '9+' else int(x)
        all_sv = sorted(set(list(vl_sg_pivot.keys()) + list(vl_fom_pivot.keys())), key=sort_key)
        vl_labels = ["Regelstudienzeit" if sv == '0' else (f"{sv} VS" if sv == '9+' else f"{sv}. VS") for sv in all_sv]

        vl_sg_vals = [vl_sg_pivot.get(sv, 0) for sv in all_sv]
        vl_fom_vals = [vl_fom_pivot.get(sv, 0) for sv in all_sv]
        total_fom = sum(vl_fom_vals) or 1
        vl_pct = [round(vl_sg_pivot.get(sv, 0) / max(vl_fom_pivot.get(sv, 0), 1) * 100, 1) for sv in all_sv]

        # Per-HSZ
        hsz_set_se = sorted(set(r.get('HSZ') for r in fs_sg if r.get('HSZ')) |
                            set(r.get('HSZ') for r in vl_sg if r.get('HSZ')))
        hsz_detail = {}
        for hsz in hsz_set_se:
            h_fs = [r for r in fs_sg if r.get('HSZ') == hsz]
            h_vl = [r for r in vl_sg if r.get('HSZ') == hsz]
            h_sg_pcts = calc_fachsem_pct(h_fs, fs_labels_num)
            h_vl_pivot = calc_verlaengerung(h_vl)
            h_vl_vals = [h_vl_pivot.get(sv, 0) for sv in all_sv]
            hsz_detail[hsz] = {
                'fachsemester_sg': h_sg_pcts,
                'verlaengerung_sg': h_vl_vals
            }

        data = {
            'fachsemester_labels': fs_labels,
            'fachsemester_sg': sg_pcts,
            'fachsemester_fom': fom_pcts,
            'verlaengerung_labels': vl_labels,
            'verlaengerung_fom': vl_fom_vals,
            'verlaengerung_sg': vl_sg_vals,
            'verlaengerung_pct': vl_pct,
            'hsz_detail': hsz_detail
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


# ─── Übergangsquote: Hilfsfunktionen ───
def _classify_uebergang(row):
    """Classify a bachelor->master transition."""
    if not row.get('M_PK'):
        return 'kein_master'
    same_hsz = row['B_HSZ_K'] == row.get('M_HSZ_K')
    b_ex = row['B_ExDatum']
    m_im = row['M_ImDatum']
    if b_ex and m_im:
        diff_days = (b_ex - m_im).days
        sem_diff = round(diff_days / 180)
        if sem_diff > 0:
            timing = 'ueberschneidung'
        elif sem_diff == 0:
            timing = 'folgesemester'
        else:
            timing = 'pause'
    else:
        timing = 'folgesemester'
    prefix = 'am_jetzigen' if same_hsz else 'an_anderem'
    return f'{prefix}_{timing}'


def _dedup_uebergang(rows):
    """Pro Person nur den nächsten Master behalten."""
    seen = {}
    deduped = []
    for r in rows:
        pid = r['PersonenFID']
        if not r.get('M_PK'):
            if pid not in seen:
                seen[pid] = True
                deduped.append(r)
        else:
            key = pid
            if key not in seen or seen[key] is True:
                seen[key] = r
                deduped.append(r)
            else:
                prev = seen[key]
                if r.get('M_ImDatum') and prev.get('M_ImDatum') and r['M_ImDatum'] < prev['M_ImDatum']:
                    deduped.remove(prev)
                    seen[key] = r
                    deduped.append(r)
    return deduped


def _compute_uebergang_stats(rows, kohorten_set):
    """Berechnet herkunft-Dict, master_total_per_kohorte, master_sg_counts."""
    herkunft_keys = ['kein_master', 'am_jetzigen_hsz', 'am_jetzigen_ueberschneidung',
                     'am_jetzigen_folgesemester', 'am_jetzigen_pause',
                     'an_anderem_hsz', 'an_anderem_ueberschneidung',
                     'an_anderem_folgesemester', 'an_anderem_pause']
    herkunft = {k: [] for k in herkunft_keys}
    master_sg_counts = {}
    master_total_per_kohorte = {}

    for kohorte in kohorten_set:
        kohorte_rows = [r for r in rows if r.get('B_Kohorte') and str(r['B_Kohorte']) == kohorte]
        total = len(kohorte_rows) or 1
        cats = {}
        for r in kohorte_rows:
            cat = _classify_uebergang(r)
            cats[cat] = cats.get(cat, 0) + 1
            if r.get('M_SG'):
                master_sg_counts.setdefault(r['M_SG'], {}).setdefault(kohorte, 0)
                master_sg_counts[r['M_SG']][kohorte] += 1

        master_total_per_kohorte[kohorte] = total - cats.get('kein_master', 0)

        herkunft['kein_master'].append(round(cats.get('kein_master', 0) / total * 100, 1))
        am_j = sum(v for k, v in cats.items() if k.startswith('am_jetzigen'))
        herkunft['am_jetzigen_hsz'].append(round(am_j / total * 100, 1))
        herkunft['am_jetzigen_ueberschneidung'].append(round(cats.get('am_jetzigen_ueberschneidung', 0) / total * 100, 1))
        herkunft['am_jetzigen_folgesemester'].append(round(cats.get('am_jetzigen_folgesemester', 0) / total * 100, 1))
        herkunft['am_jetzigen_pause'].append(round(cats.get('am_jetzigen_pause', 0) / total * 100, 1))
        an_a = sum(v for k, v in cats.items() if k.startswith('an_anderem'))
        herkunft['an_anderem_hsz'].append(round(an_a / total * 100, 1))
        herkunft['an_anderem_ueberschneidung'].append(round(cats.get('an_anderem_ueberschneidung', 0) / total * 100, 1))
        herkunft['an_anderem_folgesemester'].append(round(cats.get('an_anderem_folgesemester', 0) / total * 100, 1))
        herkunft['an_anderem_pause'].append(round(cats.get('an_anderem_pause', 0) / total * 100, 1))

    return herkunft, master_total_per_kohorte, master_sg_counts


def _get_fom_uebergang_avg():
    """Berechnet den FOM-weiten Übergangsquoten-Durchschnitt (gecached)."""
    cache_key = 'uebergang_fom_avg'
    cached = cache_get(cache_key)
    if cached:
        return cached

    rows = query_db(SQL_UEBERGANG_FOM)
    rows = _dedup_uebergang(rows)

    # Durchschnitt über ALLE Kohorten (analog zur SG-Berechnung)
    kohorten_set = sorted(set(str(r['B_Kohorte']) for r in rows if r.get('B_Kohorte')), reverse=True)
    if not kohorten_set:
        return [0] * 9

    herkunft, _, _ = _compute_uebergang_stats(rows, kohorten_set)
    n_kohorten = len(kohorten_set)

    herkunft_keys = ['kein_master', 'am_jetzigen_hsz', 'am_jetzigen_ueberschneidung',
                     'am_jetzigen_folgesemester', 'am_jetzigen_pause',
                     'an_anderem_hsz', 'an_anderem_ueberschneidung',
                     'an_anderem_folgesemester', 'an_anderem_pause']
    result = [round(sum(herkunft[k]) / n_kohorten, 1) if herkunft.get(k) else 0 for k in herkunft_keys]

    cache_set(cache_key, result)
    return result


@app.route('/api/steckbrief/<produktkuerzel>/uebergang')
@login_required
def uebergang(produktkuerzel):
    try:
        cache_key = f'uebergang_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        sql_ueb, p_ueb = pk_expand_sql(SQL_UEBERGANG, produktkuerzel)
        rows = query_db(sql_ueb, p_ueb)

        rows = _dedup_uebergang(rows)

        # Group by Kohorte (full semester: e.g. 2021-WS, 2022-SS)
        kohorten_set = sorted(set(str(r['B_Kohorte']) for r in rows if r.get('B_Kohorte')), reverse=True)

        herkunft, master_total_per_kohorte, master_sg_counts = _compute_uebergang_stats(rows, kohorten_set)

        # Master-Studiengänge Top 10 (Prozent bezogen auf Absolventen mit Master)
        master_sg_sorted = sorted(master_sg_counts.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
        master_studiengaenge = []
        for sg_name, kohorte_counts in master_sg_sorted:
            werte = []
            for k in kohorten_set:
                cnt = kohorte_counts.get(k, None)
                mt = master_total_per_kohorte.get(k, 0)
                if cnt is not None and mt > 0:
                    werte.append(round(cnt / mt * 100, 1))
                else:
                    werte.append(None)
            master_studiengaenge.append({'name': sg_name, 'werte': werte})

        # Übersicht (Durchschnitt aller Kohorten, wie bei Herkunft)
        uebersicht_labels = ['kein Master', 'am jetzigen HSZ', 'Überschneidung', 'Folgesemester', 'Pause',
                             'an anderem HSZ', 'Überschneidung', 'Folgesemester', 'Pause']
        uebersicht_gruppen = [None, None, 'am jetzigen HSZ', 'am jetzigen HSZ', 'am jetzigen HSZ',
                              None, 'an anderem HSZ', 'an anderem HSZ', 'an anderem HSZ']
        herkunft_keys_ue = ['kein_master', 'am_jetzigen_hsz', 'am_jetzigen_ueberschneidung',
                            'am_jetzigen_folgesemester', 'am_jetzigen_pause',
                            'an_anderem_hsz', 'an_anderem_ueberschneidung',
                            'an_anderem_folgesemester', 'an_anderem_pause']
        n_kohorten_ue = len(kohorten_set) or 1
        uebersicht_sg = [round(sum(herkunft[k]) / n_kohorten_ue, 1) if herkunft.get(k) else 0 for k in herkunft_keys_ue]

        # FOM-Durchschnitt (alle Bachelor-Studiengänge)
        uebersicht_fom = _get_fom_uebergang_avg()

        # Per-HSZ Aufschlüsselung
        hsz_set = sorted(set(r['B_HSZ'] for r in rows if r.get('B_HSZ')))
        hsz_detail = {}
        for hsz in hsz_set:
            hsz_rows = [r for r in rows if r.get('B_HSZ') == hsz]
            hsz_kohorten = sorted(set(str(r['B_Kohorte']) for r in hsz_rows if r.get('B_Kohorte')), reverse=True)
            if hsz_kohorten:
                h_herkunft, h_master_total, h_master_sg = _compute_uebergang_stats(hsz_rows, hsz_kohorten)
                n_k = len(hsz_kohorten) or 1
                herkunft_keys_h = ['kein_master', 'am_jetzigen_hsz', 'am_jetzigen_ueberschneidung',
                                   'am_jetzigen_folgesemester', 'am_jetzigen_pause',
                                   'an_anderem_hsz', 'an_anderem_ueberschneidung',
                                   'an_anderem_folgesemester', 'an_anderem_pause']
                h_uebersicht_sg = [round(sum(h_herkunft[k]) / n_k, 1) if h_herkunft.get(k) else 0 for k in herkunft_keys_h]
                # Top Master-SG
                h_master_sorted = sorted(h_master_sg.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
                h_master_studiengaenge = []
                for sg_name, kc in h_master_sorted:
                    werte = []
                    for k in hsz_kohorten:
                        cnt = kc.get(k, None)
                        mt = h_master_total.get(k, 0)
                        werte.append(round(cnt / mt * 100, 1) if cnt and mt > 0 else None)
                    h_master_studiengaenge.append({'name': sg_name, 'werte': werte})
                hsz_detail[hsz] = {
                    'kohorten': hsz_kohorten,
                    'herkunft': h_herkunft,
                    'master_studiengaenge': h_master_studiengaenge,
                    'uebersicht_sg': h_uebersicht_sg
                }

        data = {
            'kohorten': kohorten_set,
            'herkunft': herkunft,
            'master_studiengaenge': master_studiengaenge,
            'uebersicht_labels': uebersicht_labels,
            'uebersicht_gruppen': uebersicht_gruppen,
            'uebersicht_fom': uebersicht_fom,
            'uebersicht_sg': uebersicht_sg,
            'hsz_detail': hsz_detail
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/herkunft')
@login_required
def herkunft(produktkuerzel):
    try:
        cache_key = f'herkunft_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        # Internationale Varianten (_IN, _INT) herausfiltern (wie im ThemenReport)
        variants = [v for v in expand_pk(produktkuerzel) if '_IN' not in v]
        if not variants:
            variants = [produktkuerzel]
        placeholders = ','.join('?' * len(variants))
        sql_herk = SQL_HERKUNFT.replace('= ?', f'IN ({placeholders})', 1)
        p_herk = variants
        rows = query_db(sql_herk, p_herk)

        # Deduplizierung: pro Master-Eintrag nur den nächsten Bachelor behalten
        by_master = {}
        for r in rows:
            key = (r['PersonenFID'], str(r.get('M_Kohorte')), str(r.get('M_ImDatum')))
            if key not in by_master:
                by_master[key] = r
            else:
                existing = by_master[key]
                # Bevorzuge Zeile mit Bachelor-Match
                if not existing.get('B_PK') and r.get('B_PK'):
                    by_master[key] = r
                elif existing.get('B_PK') and r.get('B_PK'):
                    # Beide haben Bachelor: nächsten (neuestes ExDatum) behalten
                    if r.get('B_ExDatum') and existing.get('B_ExDatum') and r['B_ExDatum'] > existing['B_ExDatum']:
                        by_master[key] = r
        rows = list(by_master.values())

        kohorten_set = sorted(set(str(r['M_Kohorte']) for r in rows if r.get('M_Kohorte')), reverse=True)

        def classify(row):
            if not row.get('B_PK'):
                return 'nicht_intern'
            same_hsz = row['M_HSZ_K'] == row.get('B_HSZ_K')
            m_im = row['M_ImDatum']
            b_ex = row['B_ExDatum']
            if b_ex and m_im:
                # Original: ROUND((TO_DAYS(Exmatrikulation) - TO_DAYS(ImmaSeit)) / 30 / 6, 0)
                diff_days = (b_ex - m_im).days
                sem_diff = round(diff_days / 180)
                if sem_diff > 0:
                    timing = 'ueberschneidung'
                elif sem_diff == 0:
                    timing = 'folgesemester'
                else:
                    timing = 'pause'
            else:
                timing = 'folgesemester'
            prefix = 'am_jetzigen' if same_hsz else 'an_anderem'
            return f'{prefix}_{timing}'

        herkunft_keys = ['nicht_intern', 'am_jetzigen_hsz', 'am_jetzigen_ueberschneidung',
                         'am_jetzigen_folgesemester', 'am_jetzigen_pause',
                         'an_anderem_hsz', 'an_anderem_ueberschneidung',
                         'an_anderem_folgesemester', 'an_anderem_pause']
        herkunft = {k: [] for k in herkunft_keys}
        bachelor_sg_counts = {}  # {sg: {kohorte: count}}
        bachelor_sg_counts_gleich = {}  # am jetzigen HSZ
        bachelor_sg_counts_anders = {}  # an anderem HSZ
        studienrichtung_counts = {}
        studienrichtung_counts_gleich = {}
        studienrichtung_counts_anders = {}
        kohorte_totals = {}

        for kohorte in kohorten_set:
            kohorte_rows = [r for r in rows if r.get('M_Kohorte') and str(r['M_Kohorte']) == kohorte]
            total = len(kohorte_rows) or 1
            kohorte_totals[kohorte] = total
            cats = {}
            for r in kohorte_rows:
                cat = classify(r)
                cats[cat] = cats.get(cat, 0) + 1
                if r.get('B_SG'):
                    bachelor_sg_counts.setdefault(r['B_SG'], {}).setdefault(kohorte, 0)
                    bachelor_sg_counts[r['B_SG']][kohorte] += 1
                    same_hsz = r.get('B_HSZ_K') and r.get('M_HSZ_K') and r['B_HSZ_K'] == r['M_HSZ_K']
                    if same_hsz:
                        bachelor_sg_counts_gleich.setdefault(r['B_SG'], {}).setdefault(kohorte, 0)
                        bachelor_sg_counts_gleich[r['B_SG']][kohorte] += 1
                    else:
                        bachelor_sg_counts_anders.setdefault(r['B_SG'], {}).setdefault(kohorte, 0)
                        bachelor_sg_counts_anders[r['B_SG']][kohorte] += 1
                if r.get('B_Familie'):
                    studienrichtung_counts.setdefault(r['B_Familie'], {}).setdefault(kohorte, 0)
                    studienrichtung_counts[r['B_Familie']][kohorte] += 1
                    same_hsz = r.get('B_HSZ_K') and r.get('M_HSZ_K') and r['B_HSZ_K'] == r['M_HSZ_K']
                    if same_hsz:
                        studienrichtung_counts_gleich.setdefault(r['B_Familie'], {}).setdefault(kohorte, 0)
                        studienrichtung_counts_gleich[r['B_Familie']][kohorte] += 1
                    else:
                        studienrichtung_counts_anders.setdefault(r['B_Familie'], {}).setdefault(kohorte, 0)
                        studienrichtung_counts_anders[r['B_Familie']][kohorte] += 1

            herkunft['nicht_intern'].append(round(cats.get('nicht_intern', 0) / total * 100, 1))
            am_j = sum(v for k, v in cats.items() if k.startswith('am_jetzigen'))
            herkunft['am_jetzigen_hsz'].append(round(am_j / total * 100, 1))
            herkunft['am_jetzigen_ueberschneidung'].append(round(cats.get('am_jetzigen_ueberschneidung', 0) / total * 100, 1))
            herkunft['am_jetzigen_folgesemester'].append(round(cats.get('am_jetzigen_folgesemester', 0) / total * 100, 1))
            herkunft['am_jetzigen_pause'].append(round(cats.get('am_jetzigen_pause', 0) / total * 100, 1))
            an_a = sum(v for k, v in cats.items() if k.startswith('an_anderem'))
            herkunft['an_anderem_hsz'].append(round(an_a / total * 100, 1))
            herkunft['an_anderem_ueberschneidung'].append(round(cats.get('an_anderem_ueberschneidung', 0) / total * 100, 1))
            herkunft['an_anderem_folgesemester'].append(round(cats.get('an_anderem_folgesemester', 0) / total * 100, 1))
            herkunft['an_anderem_pause'].append(round(cats.get('an_anderem_pause', 0) / total * 100, 1))

        def build_top10(counts_dict):
            sorted_items = sorted(counts_dict.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
            return [{'name': name, 'werte': [round(kc.get(k, 0) / kohorte_totals[k] * 100, 1) if kc.get(k) else None for k in kohorten_set]} for name, kc in sorted_items]

        def build_top10_abs(counts_dict):
            sorted_items = sorted(counts_dict.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
            return [{'name': name, 'werte': [kc.get(k, None) for k in kohorten_set]} for name, kc in sorted_items]

        bachelor_studiengaenge = build_top10(bachelor_sg_counts)
        bachelor_studiengaenge_gleich = build_top10(bachelor_sg_counts_gleich)
        bachelor_studiengaenge_anders = build_top10(bachelor_sg_counts_anders)

        top_studienrichtungen = build_top10_abs(bachelor_sg_counts)
        top_studienrichtungen_gleich = build_top10_abs(bachelor_sg_counts_gleich)
        top_studienrichtungen_anders = build_top10_abs(bachelor_sg_counts_anders)

        uebersicht_labels = ['kein Bachelor an der FOM', 'am jetzigen HSZ', 'Überschneidung', 'Folgesemester', 'Pause',
                             'an anderem HSZ', 'Überschneidung', 'Folgesemester', 'Pause']
        uebersicht_gruppen = [None, None, 'am jetzigen HSZ', 'am jetzigen HSZ', 'am jetzigen HSZ',
                              None, 'an anderem HSZ', 'an anderem HSZ', 'an anderem HSZ']
        n_kohorten = len(kohorten_set) or 1
        uebersicht_sg = [round(sum(herkunft[k]) / n_kohorten, 1) if herkunft[k] else 0 for k in herkunft_keys]
        uebersicht_fom = uebersicht_sg  # Placeholder for FOM-wide
        zeitraum = f"{kohorten_set[-1]} bis {kohorten_set[0]}" if kohorten_set else ''

        # Per-HSZ Aufschlüsselung
        hsz_set_h = sorted(set(r['M_HSZ'] for r in rows if r.get('M_HSZ')))
        hsz_detail = {}
        for hsz in hsz_set_h:
            h_rows = [r for r in rows if r.get('M_HSZ') == hsz]
            h_kohorten = sorted(set(str(r['M_Kohorte']) for r in h_rows if r.get('M_Kohorte')), reverse=True)
            if not h_kohorten:
                continue
            h_herkunft = {k: [] for k in herkunft_keys}
            h_bach_counts = {}
            h_kohorte_totals = {}
            for hk in h_kohorten:
                hk_rows = [r for r in h_rows if r.get('M_Kohorte') and str(r['M_Kohorte']) == hk]
                htotal = len(hk_rows) or 1
                h_kohorte_totals[hk] = htotal
                hcats = {}
                for r in hk_rows:
                    hcat = classify(r)
                    hcats[hcat] = hcats.get(hcat, 0) + 1
                    if r.get('B_SG'):
                        h_bach_counts.setdefault(r['B_SG'], {}).setdefault(hk, 0)
                        h_bach_counts[r['B_SG']][hk] += 1
                h_herkunft['nicht_intern'].append(round(hcats.get('nicht_intern', 0) / htotal * 100, 1))
                am_j_h = sum(v for k, v in hcats.items() if k.startswith('am_jetzigen'))
                h_herkunft['am_jetzigen_hsz'].append(round(am_j_h / htotal * 100, 1))
                h_herkunft['am_jetzigen_ueberschneidung'].append(round(hcats.get('am_jetzigen_ueberschneidung', 0) / htotal * 100, 1))
                h_herkunft['am_jetzigen_folgesemester'].append(round(hcats.get('am_jetzigen_folgesemester', 0) / htotal * 100, 1))
                h_herkunft['am_jetzigen_pause'].append(round(hcats.get('am_jetzigen_pause', 0) / htotal * 100, 1))
                an_a_h = sum(v for k, v in hcats.items() if k.startswith('an_anderem'))
                h_herkunft['an_anderem_hsz'].append(round(an_a_h / htotal * 100, 1))
                h_herkunft['an_anderem_ueberschneidung'].append(round(hcats.get('an_anderem_ueberschneidung', 0) / htotal * 100, 1))
                h_herkunft['an_anderem_folgesemester'].append(round(hcats.get('an_anderem_folgesemester', 0) / htotal * 100, 1))
                h_herkunft['an_anderem_pause'].append(round(hcats.get('an_anderem_pause', 0) / htotal * 100, 1))
            n_k_h = len(h_kohorten) or 1
            h_uebersicht_sg = [round(sum(h_herkunft[k]) / n_k_h, 1) if h_herkunft[k] else 0 for k in herkunft_keys]
            # Bachelor-SG Top 10 für dieses HSZ
            h_bach_sorted = sorted(h_bach_counts.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]
            h_bachelor_sg = [{'name': name, 'werte': [round(kc.get(k, 0) / h_kohorte_totals[k] * 100, 1) if kc.get(k) else None for k in h_kohorten]} for name, kc in h_bach_sorted]
            hsz_detail[hsz] = {
                'kohorten': h_kohorten,
                'herkunft': h_herkunft,
                'bachelor_studiengaenge': h_bachelor_sg,
                'uebersicht_sg': h_uebersicht_sg
            }

        data = {
            'kohorten': kohorten_set,
            'zeitraum': zeitraum,
            'herkunft': herkunft,
            'bachelor_studiengaenge': bachelor_studiengaenge,
            'bachelor_studiengaenge_gleich': bachelor_studiengaenge_gleich,
            'bachelor_studiengaenge_anders': bachelor_studiengaenge_anders,
            'top_studienrichtungen': top_studienrichtungen,
            'top_studienrichtungen_gleich': top_studienrichtungen_gleich,
            'top_studienrichtungen_anders': top_studienrichtungen_anders,
            'uebersicht_labels': uebersicht_labels,
            'uebersicht_gruppen': uebersicht_gruppen,
            'uebersicht_fom': uebersicht_fom,
            'uebersicht_sg': uebersicht_sg,
            'hsz_detail': hsz_detail
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/zuzahler')
@login_required
def zuzahler(produktkuerzel):
    try:
        cache_key = f'zuzahler_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        variants = expand_pk(produktkuerzel)
        pk_placeholders = ','.join('?' * len(variants))

        # FOM-weite Daten global cachen (CTE-basiert, ohne Temp-Tabellen)
        fom_rows = cache_get('_global_zuzahler_fom')
        if not fom_rows:
            fom_rows = query_db(SQL_ZUZAHLER_FOM)
            cache_set('_global_zuzahler_fom', fom_rows)

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # 1) #gs_zuz: Gesamtstudierende (PK-gefiltert)
            try: cursor.execute("DROP TABLE IF EXISTS #gs_zuz")
            except Exception: pass
            cursor.execute("""CREATE TABLE #gs_zuz (
                Semesterkuerzel VARCHAR(10), StudienEintragID INT,
                PersonenFID INT, Nachname NVARCHAR(200), SemesterStart DATE,
                HSZ NVARCHAR(100)
            )""")
            cursor.execute(f"""
                INSERT INTO #gs_zuz
                SELECT DISTINCT
                    sz.Semesterkuerzel, se.StudienEintragID, se.PersonenFID, p.Nachname,
                    CASE WHEN RIGHT(sz.Semesterkuerzel, 2) = 'SS'
                        THEN CAST(CONCAT(LEFT(sz.Semesterkuerzel, 4), '-03-01') AS DATE)
                        ELSE CAST(CONCAT(LEFT(sz.Semesterkuerzel, 4), '-09-01') AS DATE)
                    END,
                    l.Hochschulzentrum
                FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
                INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
                INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
                WHERE l.Institut = 'FOM' AND p.Testperson = 0
                  AND sg.StatusGruppe = 'Gesamtstudierende mit UV'
                  AND CAST(LEFT(sz.Semesterkuerzel, 4) AS INT) >= YEAR(GETDATE()) - 4
                  AND sz.Semesterkuerzel <= CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
                  AND l.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
                  AND l.Ausrichtung = 'national'
                  AND l.Produktkuerzel IN ({pk_placeholders})
            """, variants)

            # 2) #zuz: Zuzahler mit FirmenFID
            try: cursor.execute("DROP TABLE IF EXISTS #zuz")
            except Exception: pass
            cursor.execute("""CREATE TABLE #zuz (
                Semesterkuerzel VARCHAR(10), StudienEintragID INT, FirmenFID INT
            )""")
            cursor.execute("""
                INSERT INTO #zuz
                SELECT gs.Semesterkuerzel, gs.StudienEintragID,
                    COALESCE(
                        CASE WHEN ztn.FirmenFID > 0 THEN ztn.FirmenFID END,
                        CASE WHEN r_match.FirmenFID > 0 THEN r_match.FirmenFID END
                    ) AS FirmenFID
                FROM #gs_zuz gs
                LEFT JOIN BCW_STA.mariadb.t_ZahlungenTn ztn
                    ON ztn.StudiengaengeTNID = gs.StudienEintragID
                    AND gs.SemesterStart BETWEEN TRY_CAST(ztn.LaufzeitVon AS DATE) AND TRY_CAST(ztn.LaufzeitBis AS DATE)
                    AND ztn.KostenUebernahmeDurch = 'Arbeitgeber'
                LEFT JOIN (
                    SELECT r.RechnungsID, r.PersonenFID, r.FirmenFID,
                           TRY_CAST(r.VonTeilnahme AS DATE) AS VonTeilnahme,
                           TRY_CAST(r.BisTeilnahme AS DATE) AS BisTeilnahme,
                           TRY_CAST(r.Ausgeschieden AS DATE) AS Ausgeschieden,
                           r.RechEmpfaenger
                    FROM BCW_STA.mariadb.t_rechnungen r
                    WHERE NOT EXISTS (
                        SELECT 1 FROM BCW_STA.mariadb.t_rechnungen_deaktiviert d WHERE d.RechnungsFID = r.RechnungsID
                    )
                    AND r.MatrikelNr <> r.DebitorenNr
                    AND LTRIM(RTRIM(r.RechEmpfaenger)) NOT IN ('Mitarbeiter')
                ) r_match ON r_match.PersonenFID = gs.PersonenFID
                    AND r_match.VonTeilnahme <= gs.SemesterStart
                    AND r_match.BisTeilnahme >= gs.SemesterStart
                    AND r_match.Ausgeschieden >= gs.SemesterStart
                    AND gs.Nachname IS NOT NULL AND gs.Nachname <> ''
                    AND LTRIM(RTRIM(r_match.RechEmpfaenger)) NOT LIKE '%' + gs.Nachname + '%'
                WHERE (ztn.ID IS NOT NULL OR r_match.RechnungsID IS NOT NULL)
            """)

            # 3) Overview: Total + Zuzahler pro Semester
            cursor.execute("""
                SELECT gs.Semesterkuerzel,
                    COUNT(DISTINCT gs.StudienEintragID) AS Total,
                    COUNT(DISTINCT z.StudienEintragID) AS Zuzahler
                FROM #gs_zuz gs
                LEFT JOIN #zuz z ON z.StudienEintragID = gs.StudienEintragID
                    AND z.Semesterkuerzel = gs.Semesterkuerzel
                GROUP BY gs.Semesterkuerzel
                ORDER BY gs.Semesterkuerzel
            """)
            columns = [col[0] for col in cursor.description]
            sg_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            # Auf 7 Semester begrenzen (aktuelles + letzte 6), dann absteigend
            sg_rows = list(reversed(_semester_filter_7(sg_rows)))

            # 3b) Per-HSZ Overview
            cursor.execute("""
                SELECT gs.HSZ, gs.Semesterkuerzel,
                    COUNT(DISTINCT gs.StudienEintragID) AS Total,
                    COUNT(DISTINCT z.StudienEintragID) AS Zuzahler
                FROM #gs_zuz gs
                LEFT JOIN #zuz z ON z.StudienEintragID = gs.StudienEintragID
                    AND z.Semesterkuerzel = gs.Semesterkuerzel
                GROUP BY gs.HSZ, gs.Semesterkuerzel
                ORDER BY gs.HSZ, gs.Semesterkuerzel
            """)
            columns_hsz = [col[0] for col in cursor.description]
            hsz_rows_raw = [dict(zip(columns_hsz, row)) for row in cursor.fetchall()]

            # 4) Top 10 Firmen (mit Namens-Deduplizierung)
            cursor.execute("""
                WITH firma_sem AS (
                    SELECT z.FirmenFID, z.Semesterkuerzel,
                           COUNT(DISTINCT z.StudienEintragID) AS Anzahl
                    FROM #zuz z
                    WHERE z.FirmenFID IS NOT NULL AND z.FirmenFID > 0
                    GROUP BY z.FirmenFID, z.Semesterkuerzel
                ),
                firma_namen AS (
                    SELECT fs.FirmenFID, fs.Semesterkuerzel, fs.Anzahl,
                        LTRIM(RTRIM(REPLACE(REPLACE(f.Firmenname, CHAR(13)+CHAR(10), ' '), CHAR(10), ' '))) AS Firmenname
                    FROM firma_sem fs
                    INNER JOIN BCW_STA.mariadb.t_firmen f ON f.FirmenID = fs.FirmenFID
                    WHERE f.Firmenname IS NOT NULL
                      AND LEN(LTRIM(RTRIM(f.Firmenname))) >= 3
                      AND f.Firmenname NOT LIKE ',%'
                      AND f.Firmenname NOT LIKE '%, z. Hd.%'
                      AND f.Firmenname NOT LIKE CHAR(10) + '%'
                ),
                merged AS (
                    SELECT Firmenname, Semesterkuerzel,
                           SUM(Anzahl) AS Anzahl
                    FROM firma_namen
                    GROUP BY Firmenname, Semesterkuerzel
                ),
                firma_total AS (
                    SELECT Firmenname, SUM(Anzahl) AS GesamtAnzahl
                    FROM merged
                    GROUP BY Firmenname
                ),
                top10 AS (
                    SELECT TOP 15 Firmenname, GesamtAnzahl
                    FROM firma_total
                    ORDER BY GesamtAnzahl DESC
                )
                SELECT t.Firmenname, m.Semesterkuerzel, m.Anzahl
                FROM top10 t
                LEFT JOIN merged m ON m.Firmenname = t.Firmenname
                ORDER BY t.GesamtAnzahl DESC, t.Firmenname, m.Semesterkuerzel
            """)
            columns_t = [col[0] for col in cursor.description]
            top10_rows = [dict(zip(columns_t, row)) for row in cursor.fetchall()]

            # 4b) Top 10 Firmen per HSZ
            cursor.execute("""
                WITH firma_sem AS (
                    SELECT gs.HSZ, z.FirmenFID, z.Semesterkuerzel,
                           COUNT(DISTINCT z.StudienEintragID) AS Anzahl
                    FROM #zuz z
                    INNER JOIN #gs_zuz gs ON gs.StudienEintragID = z.StudienEintragID AND gs.Semesterkuerzel = z.Semesterkuerzel
                    WHERE z.FirmenFID IS NOT NULL AND z.FirmenFID > 0
                    GROUP BY gs.HSZ, z.FirmenFID, z.Semesterkuerzel
                ),
                firma_namen AS (
                    SELECT fs.HSZ, fs.FirmenFID, fs.Semesterkuerzel, fs.Anzahl,
                        LTRIM(RTRIM(REPLACE(REPLACE(f.Firmenname, CHAR(13)+CHAR(10), ' '), CHAR(10), ' '))) AS Firmenname
                    FROM firma_sem fs
                    INNER JOIN BCW_STA.mariadb.t_firmen f ON f.FirmenID = fs.FirmenFID
                    WHERE f.Firmenname IS NOT NULL
                      AND LEN(LTRIM(RTRIM(f.Firmenname))) >= 3
                      AND f.Firmenname NOT LIKE ',%'
                      AND f.Firmenname NOT LIKE '%, z. Hd.%'
                      AND f.Firmenname NOT LIKE CHAR(10) + '%'
                ),
                merged AS (
                    SELECT HSZ, Firmenname, Semesterkuerzel,
                           SUM(Anzahl) AS Anzahl
                    FROM firma_namen
                    GROUP BY HSZ, Firmenname, Semesterkuerzel
                ),
                firma_total AS (
                    SELECT HSZ, Firmenname, SUM(Anzahl) AS GesamtAnzahl
                    FROM merged
                    GROUP BY HSZ, Firmenname
                )
                SELECT ft.HSZ, ft.Firmenname, ft.GesamtAnzahl, m.Semesterkuerzel, m.Anzahl
                FROM firma_total ft
                LEFT JOIN merged m ON m.Firmenname = ft.Firmenname AND m.HSZ = ft.HSZ
                ORDER BY ft.HSZ, ft.GesamtAnzahl DESC, ft.Firmenname, m.Semesterkuerzel
            """)
            cols_th = [col[0] for col in cursor.description]
            top10_hsz_rows = [dict(zip(cols_th, row)) for row in cursor.fetchall()]

            # Cleanup
            try: cursor.execute("DROP TABLE IF EXISTS #zuz; DROP TABLE IF EXISTS #gs_zuz")
            except Exception: pass

        finally:
            release_connection(conn)

        # Alle verfügbaren Semester ermitteln (absteigend sortiert)
        all_semesters = [r['Semesterkuerzel'] for r in sg_rows]

        fom_map = {r['Semesterkuerzel']: r for r in fom_rows}

        def fmt_sem(sk):
            return f"{'WS' if sk.endswith('WS') else 'SS'}-{sk[:4]}"

        semester = [fmt_sem(r['Semesterkuerzel']) for r in sg_rows]
        absolut = [int(r['Zuzahler']) for r in sg_rows]
        pct_sg = [round(int(r['Zuzahler']) / max(int(r['Total']), 1) * 100, 1) for r in sg_rows]
        pct_fom = []
        for r in sg_rows:
            fom_r = fom_map.get(r['Semesterkuerzel'])
            if fom_r:
                pct_fom.append(round(int(fom_r['Zuzahler']) / max(int(fom_r['Total']), 1) * 100, 1))
            else:
                pct_fom.append(0)

        # Top10 aufbereiten: { name, werte[] } pro Firma
        top10 = []
        if top10_rows:
            current_name = None
            current_werte = {}
            for r in top10_rows:
                name = (r['Firmenname'] or '').strip()
                # Müll-Firmennamen filtern (z.B. ", z. Hd. Frau...")
                if not name or name.startswith(',') or name.startswith('z. Hd.') or len(name) < 3:
                    continue
                if name != current_name:
                    if current_name is not None:
                        top10.append({
                            'name': current_name,
                            'werte': [current_werte.get(s, None) for s in all_semesters]
                        })
                    current_name = name
                    current_werte = {}
                current_werte[r['Semesterkuerzel']] = int(r['Anzahl'])
            if current_name is not None:
                top10.append({
                    'name': current_name,
                    'werte': [current_werte.get(s, None) for s in all_semesters]
                })
            top10 = top10[:10]

        # Per-HSZ Zuzahler
        hsz_detail = {}
        hsz_set_z = sorted(set(r.get('HSZ') for r in hsz_rows_raw if r.get('HSZ')))

        # Per-HSZ Top10 aufbereiten
        hsz_top10_map = {}
        if top10_hsz_rows:
            for hsz in hsz_set_z:
                hsz_firma_rows = [r for r in top10_hsz_rows if r.get('HSZ') == hsz]
                h_all_sem = sorted(set(r['Semesterkuerzel'] for r in hsz_firma_rows if r.get('Semesterkuerzel')))
                h_top10 = []
                current_name = None
                current_werte = {}
                for r in hsz_firma_rows:
                    name = (r['Firmenname'] or '').strip()
                    if not name or len(name) < 3:
                        continue
                    if name != current_name:
                        if current_name is not None:
                            h_top10.append({'name': current_name, 'werte': [current_werte.get(s, None) for s in all_semesters]})
                        current_name = name
                        current_werte = {}
                    if r.get('Semesterkuerzel') and r.get('Anzahl'):
                        current_werte[r['Semesterkuerzel']] = int(r['Anzahl'])
                if current_name is not None:
                    h_top10.append({'name': current_name, 'werte': [current_werte.get(s, None) for s in all_semesters]})
                hsz_top10_map[hsz] = h_top10[:10]

        for hsz in hsz_set_z:
            h_rows = [r for r in hsz_rows_raw if r.get('HSZ') == hsz]
            h_rows_filtered = list(reversed(_semester_filter_7(h_rows)))
            if not h_rows_filtered:
                continue
            h_semester = [fmt_sem(r['Semesterkuerzel']) for r in h_rows_filtered]
            h_absolut = [int(r['Zuzahler']) for r in h_rows_filtered]
            h_pct_sg = [round(int(r['Zuzahler']) / max(int(r['Total']), 1) * 100, 1) for r in h_rows_filtered]
            hsz_detail[hsz] = {
                'semester': h_semester,
                'absolut': h_absolut,
                'pct_sg': h_pct_sg,
                'top10': hsz_top10_map.get(hsz, []),
                'gesamtergebnis': h_absolut
            }

        data = {
            'semester': semester,
            'absolut': absolut,
            'pct_sg': pct_sg,
            'pct_fom': pct_fom,
            'top10': top10,
            'gesamtergebnis': absolut,
            'hsz_detail': hsz_detail
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/vertiefungsrichtungen')
@login_required
def vertiefungsrichtungen(produktkuerzel):
    try:
        cache_key = f'vertiefungsrichtungen_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        sql_vr, p_vr = pk_expand_sql(SQL_VERTIEFUNGSRICHTUNGEN, produktkuerzel)
        rows = query_db(sql_vr, p_vr)

        if not rows:
            return jsonify(success=True, data=None)

        # Alle Semester sammeln, auf 7 begrenzen (aktuelles + letzte 6)
        cur_sem = _aktuelles_semester()
        all_semesters = sorted(set(r['Semesterkuerzel'] for r in rows if r['Semesterkuerzel']))
        all_semesters = [s for s in all_semesters if s <= cur_sem][-7:]
        # Nur Daten innerhalb des Zeitfensters behalten
        sem_set = set(all_semesters)
        rows = [r for r in rows if r['Semesterkuerzel'] in sem_set]

        def fmt_sem(sk):
            if not sk:
                return '?'
            return f"{'WS' if sk.endswith('WS') else 'SS'}-{sk[:4]}"

        # Daten nach Wahlart aufteilen
        vr_rows = [r for r in rows if r['Wahlart'] == 'Vertiefungsrichtung']
        wp_rows = [r for r in rows if r['Wahlart'] == 'Wahlpflichtmodul']

        def build_table(subset, semesters):
            from collections import OrderedDict
            groups = OrderedDict()
            for r in subset:
                vname = r['Vertiefungsname']
                mname = r['Modulname']
                sem = r['Semesterkuerzel']
                cnt = int(r['Anzahl'])
                if vname not in groups:
                    groups[vname] = OrderedDict()
                if mname not in groups[vname]:
                    groups[vname][mname] = {}
                groups[vname][mname][sem] = groups[vname][mname].get(sem, 0) + cnt

            items = []
            gesamt = [0] * len(semesters)
            for vname, module in groups.items():
                group_werte = []
                for si, sem in enumerate(semesters):
                    total = sum(m.get(sem, 0) for m in module.values())
                    group_werte.append(total)
                    gesamt[si] += total
                items.append({'name': vname, 'isGroup': True, 'werte': group_werte})
                sorted_modules = sorted(module.items(), key=lambda x: sum(x[1].values()), reverse=True)
                for mname, sem_counts in sorted_modules:
                    werte = [sem_counts.get(sem, 0) for sem in semesters]
                    if sum(werte) > 0:
                        items.append({'name': f'  {mname}', 'isGroup': False, 'werte': werte})
            return items, gesamt

        semester_labels = [fmt_sem(s) for s in all_semesters]

        data = {}

        if vr_rows:
            vr_items, vr_gesamt = build_table(vr_rows, all_semesters)
            data['wahlmodule_semester'] = semester_labels
            data['wahlmodule'] = vr_items
            data['wahlmodule_gesamt'] = vr_gesamt

        if wp_rows:
            wp_items, wp_gesamt = build_table(wp_rows, all_semesters)
            data['wp_semester'] = semester_labels
            data['wp_module'] = wp_items
            data['wp_gesamt'] = wp_gesamt

        # ─── Hochschulzertifikate (ab WS21) ───
        try:
            sql_hz, p_hz = pk_expand_sql(SQL_HOCHSCHULZERTIFIKATE, produktkuerzel, count=1)
            hz_rows = query_db(sql_hz, p_hz)
            if hz_rows:
                hz_blocks = sorted(set(r['Block'] for r in hz_rows if r['Block']))
                hz_names = sorted(set(r['Zertifikat'] for r in hz_rows))
                # Pivot: pro Zertifikat eine Zeile mit Werten pro Block
                zertifikate = []
                for name in hz_names:
                    werte = []
                    for block in hz_blocks:
                        val = sum(r['Anzahl'] for r in hz_rows if r['Zertifikat'] == name and r['Block'] == block)
                        werte.append(val if val > 0 else None)
                    if any(w for w in werte):
                        zertifikate.append({'name': name, 'werte': werte})
                if zertifikate:
                    data['zertifikate_semester'] = hz_blocks
                    data['zertifikate'] = zertifikate
        except Exception as hz_err:
            print(f"[HZ] Fehler: {hz_err}")

        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/api/steckbrief/<produktkuerzel>/rahmendaten')
@login_required
def rahmendaten(produktkuerzel):
    try:
        cache_key = f'rahmendaten_{produktkuerzel}'
        cached = cache_get(cache_key)
        if cached:
            return jsonify(success=True, data=cached, cached=True)

        sql_rahmen, p_rahmen = pk_expand_sql(SQL_RAHMENDATEN, produktkuerzel)
        rahmen_rows = query_db(sql_rahmen, p_rahmen)

        # Studienformate aus t_lehrgaenge (aktuelles Semester)
        sql_sf, p_sf = pk_expand_sql(SQL_STUDIENFORMATE, produktkuerzel)
        sf_rows = query_db(sql_sf, p_sf)
        studienformate = [r['Studienformat'] for r in sf_rows if r.get('Studienformat')]

        zeitmodelle = [r['Zeitmodell'] for r in rahmen_rows if r.get('Zeitmodell')]
        erstes_angebot = None
        for r in rahmen_rows:
            ea = r.get('ErstesAngebot')
            if ea:
                if erstes_angebot is None or str(ea) < str(erstes_angebot):
                    erstes_angebot = ea

        im_angebot_seit = ''
        if erstes_angebot:
            from datetime import datetime
            if hasattr(erstes_angebot, 'month'):
                m = erstes_angebot.month
                y = erstes_angebot.year
            else:
                dt = datetime.strptime(str(erstes_angebot)[:10], '%Y-%m-%d')
                m, y = dt.month, dt.year
            im_angebot_seit = f"{'WS' if m >= 9 else 'SS'} {y}"

        # UE data (grouped by Fachsemester)
        try:
            # CTE: nur Standard-Studiengang (neueste Version)
            # Buchungen: alle Aliases (expandiert)
            variants = expand_pk(produktkuerzel)
            ph_buchungen = ','.join('?' * len(variants))
            # SQL hat 2x '= ?': 1. CTE (Standard-PK), 2. Buchungen (alle Aliases)
            sql_parts = SQL_UES.split('= ?')
            sql_ues_final = sql_parts[0] + '= ?' + sql_parts[1] + f'IN ({ph_buchungen})' + sql_parts[2]
            p_ues = [produktkuerzel] + variants
            ue_rows = query_db(sql_ues_final, p_ues)

            # Schritt 1: Module ohne Fachsemester identifizieren (nicht im Standard-VP)
            all_modules = set()
            missing_modules = set()
            for r in ue_rows:
                if r['ModulFID'] is not None:
                    mid = int(r['ModulFID'])
                    all_modules.add(mid)
                    if r['Fachsemester'] is None:
                        missing_modules.add(mid)

            # Schritt 2: Fehlende Module per VP aller Aliases nachschlagen
            vp_aliases_mapping = {}
            if missing_modules and len(variants) > 1:
                pk_ph = ','.join(['?'] * len(variants))
                mod_ph = ','.join(['?'] * len(missing_modules))
                sql_vp_al = SQL_VP_ALIASES_SEMESTER.format(
                    pk_placeholders=pk_ph, mod_placeholders=mod_ph)
                p_vp_al = variants + list(missing_modules)
                vp_al_rows = query_db(sql_vp_al, p_vp_al)
                for row in vp_al_rows:
                    vp_aliases_mapping[int(row['ModulFID'])] = int(row['Fachsemester'])

            # Schritt 3: Noch fehlende Module per Grow nachschlagen
            still_missing = missing_modules - set(vp_aliases_mapping.keys())
            grow_mapping = {}
            if still_missing:
                placeholders = ','.join(['?'] * len(still_missing))
                sql_grow = SQL_GROW_SEMESTER.format(placeholders=placeholders)
                grow_rows = query_db(sql_grow, list(still_missing))
                for gr in grow_rows:
                    grow_mapping[int(gr['ModulID'])] = int(gr['Fachsemester'])

            # Schritt 4: Aggregation - Standard-VP > Aliases-VP > Grow
            ue_semester = {}
            ue_total = {'praxis': 0, 'virtuell': 0, 'folgt': 0}
            for r in ue_rows:
                typ = r['UETyp']
                val = int(r['TotalUE'] or 0)
                if typ not in ('praxis', 'virtuell', 'folgt'):
                    continue
                modul_id = int(r['ModulFID']) if r['ModulFID'] else None
                # Fachsemester-Hierarchie: Standard-VP > Aliases-VP > Grow
                sem_vp = int(r['Fachsemester']) if r['Fachsemester'] is not None else None
                sem_aliases = vp_aliases_mapping.get(modul_id) if modul_id else None
                sem_grow = grow_mapping.get(modul_id) if modul_id else None
                sem = sem_vp if sem_vp is not None else (sem_aliases if sem_aliases is not None else sem_grow)
                sem_key = int(sem) if sem is not None else 0
                if sem_key not in ue_semester:
                    ue_semester[sem_key] = {'praxis': 0, 'virtuell': 0, 'folgt': 0}
                ue_semester[sem_key][typ] += val
                ue_total[typ] += val
            ue = ue_total
            # Sort by semester, put 0 (unassigned) last
            ue_by_semester = []
            for s in sorted(k for k in ue_semester if k > 0):
                ue_by_semester.append({'semester': s, **ue_semester[s]})
            if 0 in ue_semester:
                ue_by_semester.append({'semester': 0, **ue_semester[0]})
        except Exception:
            ue = {'praxis': 0, 'virtuell': 0, 'folgt': 0}
            ue_by_semester = []

        # Verantwortlicher Dekan aus DWH
        dekan = ''
        try:
            sql_dekan, p_dekan = pk_expand_sql(SQL_DEKAN, produktkuerzel)
            dekan_rows = query_db(sql_dekan, p_dekan)
            if dekan_rows:
                r = dekan_rows[0]
                titel = (r.get('TitelDeutsch') or '').strip()
                vorname = (r.get('Vorname') or '').strip()
                nachname = (r.get('Nachname') or '').strip()
                dekan = f"{titel} {vorname} {nachname}".strip()
        except Exception:
            pass

        # Akkreditierung aus Excel
        akkred = ''
        excel_data = EXCEL_RAHMENDATEN.get(produktkuerzel, {})
        if excel_data:
            akkred = excel_data.get('akkreditierung', '')

        data = {
            'imAngebotSeit': im_angebot_seit,
            'zeitmodelle': zeitmodelle,
            'studienformate': studienformate,
            'akkreditierungsDatum': akkred,
            'verantwortlicherDekan': dekan,
            'ue': ue,
            'ueBySemester': ue_by_semester
        }
        cache_set(cache_key, data)
        return jsonify(success=True, data=data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


# ─── Cache-Status ───
@app.route('/api/cache/status')
@login_required
def cache_status():
    """Gibt den ältesten und neuesten Cache-Timestamp zurück."""
    if not CACHE:
        return jsonify(success=True, entries=0, datenstand=None)
    timestamps = [entry['ts'] for entry in CACHE.values()]
    oldest = min(timestamps)
    from datetime import datetime
    datenstand = datetime.fromtimestamp(oldest).strftime('%d.%m.%Y')
    return jsonify(success=True, entries=len(CACHE), datenstand=datenstand)


# ─── Scheduler: Cache-Reload jeden Sonntag um 16:00 ───
def scheduled_cache_reload():
    """Leert den Cache und lädt alle Daten neu."""
    print('[Scheduler] Starte wöchentlichen Cache-Reload (Sonntag 16:00)...')
    CACHE.clear()
    with app.test_client() as client:
        resp = client.post('/api/cache/preload')
        data = resp.get_json()
        if data.get('success'):
            print(f'[Scheduler] Cache-Reload erfolgreich: {data.get("endpoints_loaded", 0)} Endpoints geladen')
        else:
            print(f'[Scheduler] Cache-Reload fehlgeschlagen: {data.get("error", "unbekannt")}')

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_cache_reload, trigger='cron', hour=3, minute=0,
                  id='daily_cache_reload', replace_existing=True)

if __name__ == '__main__':
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print('[Scheduler] Täglicher Cache-Reload geplant: 03:00 Uhr')

    print(f'\n╔════════════════════════════════════════╗')
    print(f'║  Steckbrief-Backend (Python/Flask)     ║')
    print(f'║  Port: 5000                            ║')
    print(f'║  DWH:  {DWH_HOST}  ║')
    print(f'║  Auth: {DWH_AUTHENTICATION}                       ║')
    print(f'╚════════════════════════════════════════╝\n')

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
