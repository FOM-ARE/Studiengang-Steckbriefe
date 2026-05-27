"""
Konfigurations-Modul: Liest alle Konfigurations-Tabellen aus MariaDB.
Stellt die Werte als Modul-Level-Variablen bereit, die bei Bedarf
über reload_config() neu geladen werden können.
"""
import os
import ssl
import pymysql
from dotenv import load_dotenv

load_dotenv()

# ─── MariaDB-Verbindung ───
_DB_HOST = os.getenv('DB_HOST', 'mariadb.bcw-intern.local')
_DB_PORT = int(os.getenv('DB_PORT', '3306'))
_DB_USER = os.getenv('DB_USER', 'HochschulorgaApps')
_DB_PASSWORD = os.getenv('DB_PASSWORD', '')
_DB_NAME = os.getenv('DB_NAME', 'HochschulorgaApps')
_DB_CHARSET = os.getenv('DB_CHARSET', 'utf8mb4')
_DB_SSL = os.getenv('DB_SSL', 'true').lower() == 'true'


def _get_connection():
    """Erstellt eine neue MariaDB-Verbindung."""
    kwargs = dict(
        host=_DB_HOST, port=_DB_PORT,
        user=_DB_USER, password=_DB_PASSWORD,
        database=_DB_NAME, charset=_DB_CHARSET
    )
    if _DB_SSL:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl'] = ssl_ctx
    return pymysql.connect(**kwargs)


def _query(sql):
    """Führt ein SELECT aus und gibt Liste von Dicts zurück."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [col[0] for col in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        conn.close()


# ═══════════════════════════════════════
# Konfigurationsdaten (Modul-Level)
# ═══════════════════════════════════════

# PK-Mapping: alias_pk → basis_pk
PK_MAPPING = {}

# Reverse: basis_pk → [basis_pk, alias1, alias2, ...]
PK_REVERSE = {}

# HSB-Config: hsb_code → {name, icon, farbe_hex, sort_order}
HSB_CONFIG = {}

# HSB-Sortierung: hsb_code → sort_order (für sorted())
HSB_ORDER = {}

# Excluded Hochschulzentren (Liste von Namen)
EXCLUDED_HSZ = []

# Excluded HSZ als SQL-Fragment: 'Bangalore','Pune',...
EXCLUDED_HSZ_SQL = ""

# Anrechnung-Regeln nach Regeltyp
ANRECHNUNG_REGELN = {}

# Endpoint-Parameter: {endpoint_code: {param_name: param_wert}}
ENDPOINT_PARAMS = {}

# Filterlisten: {bereich: [wert, ...]}
FILTERLISTE = {}

# SQL CASE-Fragment für PK-Mapping (verwendet in DWH-Queries)
PK_CASE_SQL = ""

# Offene-Hochschule-Gründe (für Stammdaten-Query)
OFFENE_HOCHSCHULE_GRUENDE = []
OFFENE_HOCHSCHULE_SQL = ""

# HSB-Exclude-Kürzel (für Studiengangsliste)
HSB_EXCLUDE_KUERZEL = []
HSB_EXCLUDE_SQL = ""


def _build_pk_case_sql(alias='l'):
    """Generiert ein CASE WHEN ... END SQL-Fragment aus dem PK-Mapping.
    Beispiel: CASE WHEN l.Produktkuerzel IN ('BBAb','BBAd') THEN 'BBA' ... ELSE l.Produktkuerzel END
    """
    # Reverse: basis_pk → [aliases] (ohne basis selbst)
    reverse = {}
    for alias_pk, basis_pk in PK_MAPPING.items():
        reverse.setdefault(basis_pk, []).append(alias_pk)

    lines = []
    for basis_pk, aliases in sorted(reverse.items()):
        if len(aliases) == 1:
            lines.append(f"                WHEN {alias}.Produktkuerzel = '{aliases[0]}' THEN '{basis_pk}'")
        else:
            in_list = ','.join(f"'{a}'" for a in sorted(aliases))
            lines.append(f"                WHEN {alias}.Produktkuerzel IN ({in_list}) THEN '{basis_pk}'")

    case_sql = "CASE\n" + "\n".join(lines) + f"\n                ELSE {alias}.Produktkuerzel\n            END"
    return case_sql


def _build_pk_case_for_s():
    """Generiert CASE WHEN für Alias 's' (verwendet in Studierendenzahlen-Queries)."""
    reverse = {}
    for alias_pk, basis_pk in PK_MAPPING.items():
        reverse.setdefault(basis_pk, []).append(alias_pk)

    lines = []
    for basis_pk, aliases in sorted(reverse.items()):
        if len(aliases) == 1:
            lines.append(f"                        WHEN s.Produktkuerzel = '{aliases[0]}' THEN '{basis_pk}'")
        else:
            in_list = ','.join(f"'{a}'" for a in sorted(aliases))
            lines.append(f"                        WHEN s.Produktkuerzel IN ({in_list}) THEN '{basis_pk}'")

    case_sql = "CASE\n" + "\n".join(lines) + "\n                        ELSE s.Produktkuerzel\n                    END"
    return case_sql


def reload_config():
    """Lädt alle Konfigurations-Tabellen aus MariaDB neu."""
    global PK_MAPPING, PK_REVERSE, HSB_CONFIG, HSB_ORDER
    global EXCLUDED_HSZ, EXCLUDED_HSZ_SQL
    global ANRECHNUNG_REGELN, ENDPOINT_PARAMS, FILTERLISTE
    global PK_CASE_SQL, OFFENE_HOCHSCHULE_GRUENDE, OFFENE_HOCHSCHULE_SQL
    global HSB_EXCLUDE_KUERZEL, HSB_EXCLUDE_SQL

    print('[Config] Lade Konfiguration aus MariaDB...')

    # 1) Produktkürzel-Alias
    rows = _query("""
        SELECT a.AliasPk, sg.BasisPk
        FROM RpStudiengangSteckbriefeProduktKuerzelAlias a
        JOIN RpStudiengangSteckbriefeStudiengang sg ON sg.Id = a.StudiengangId
        WHERE a.IstAktiv = 1
    """)
    PK_MAPPING = {r['AliasPk']: r['BasisPk'] for r in rows}

    # Reverse-Map: basis_pk → [basis_pk, alias1, alias2, ...]
    PK_REVERSE = {}
    for alias_pk, basis_pk in PK_MAPPING.items():
        PK_REVERSE.setdefault(basis_pk, [basis_pk])
        if alias_pk not in PK_REVERSE[basis_pk]:
            PK_REVERSE[basis_pk].append(alias_pk)

    # 2) Hochschulbereiche
    rows = _query("SELECT HsbCode, Name, Icon, FarbeHex, Sortierung FROM RpStudiengangSteckbriefeHochschulbereich WHERE IstAktiv = 1")
    HSB_CONFIG = {r['HsbCode']: {'hsb_code': r['HsbCode'], 'hsb_name': r['Name'], 'icon': r['Icon'], 'farbe_hex': r['FarbeHex'], 'sort_order': r['Sortierung']} for r in rows}
    HSB_ORDER = {r['HsbCode']: r['Sortierung'] for r in rows}

    # 3) Hochschulzentren (excluded)
    rows = _query("SELECT Name FROM RpStudiengangSteckbriefeHochschulzentrum WHERE IstAusgeschlossen = 1 AND IstAktiv = 1")
    EXCLUDED_HSZ = [r['Name'] for r in rows]
    EXCLUDED_HSZ_SQL = ','.join(f"'{h}'" for h in EXCLUDED_HSZ) if EXCLUDED_HSZ else "'__NONE__'"

    # 4) Anrechnung-Regeln
    rows = _query("SELECT Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet FROM RpStudiengangSteckbriefeAnrechnungRegel WHERE IstAktiv = 1 ORDER BY Prioritaet")
    ANRECHNUNG_REGELN = {}
    for r in rows:
        ANRECHNUNG_REGELN.setdefault(r['Regeltyp'], []).append({
            'regeltyp': r['Regeltyp'],
            'match_operator': r['AbgleichOperator'],
            'match_wert': r['AbgleichWert'],
            'kategorie': r['Kategorie'],
            'prioritaet': r['Prioritaet']
        })

    # Offene Hochschule: ANRECHNUNGSGRUND → OFFENE_HOCHSCHULE
    OFFENE_HOCHSCHULE_GRUENDE = [
        r['match_wert'] for r in ANRECHNUNG_REGELN.get('ANRECHNUNGSGRUND', [])
        if r['kategorie'] == 'OFFENE_HOCHSCHULE'
    ]
    OFFENE_HOCHSCHULE_SQL = ','.join(f"'{g}'" for g in OFFENE_HOCHSCHULE_GRUENDE) if OFFENE_HOCHSCHULE_GRUENDE else "'__NONE__'"

    # 5) Endpoint-Parameter
    rows = _query("SELECT EndpunktCode, ParamName, ParamWert FROM RpStudiengangSteckbriefeEndpunktParameter WHERE IstAktiv = 1")
    ENDPOINT_PARAMS = {}
    for r in rows:
        ENDPOINT_PARAMS.setdefault(r['EndpunktCode'], {})[r['ParamName']] = r['ParamWert']

    # 6) Filterliste
    rows = _query("SELECT Bereich, Wert, Typ FROM RpStudiengangSteckbriefeFilterliste WHERE IstAktiv = 1")
    FILTERLISTE = {}
    for r in rows:
        FILTERLISTE.setdefault(r['Bereich'], []).append(r['Wert'])

    # HSB-Exclude-Kürzel (für Studiengangliste)
    HSB_EXCLUDE_KUERZEL = FILTERLISTE.get('HSB_EXCLUDE', [])
    HSB_EXCLUDE_SQL = ','.join(f"'{k}'" for k in HSB_EXCLUDE_KUERZEL) if HSB_EXCLUDE_KUERZEL else "'__NONE__'"

    # 7) PK-CASE SQL-Fragmente
    PK_CASE_SQL = _build_pk_case_sql('l')

    print(f'[Config] Geladen: {len(PK_MAPPING)} Aliases, {len(HSB_CONFIG)} HSBs, '
          f'{len(EXCLUDED_HSZ)} excl. HSZ, {len(ANRECHNUNG_REGELN)} Regeltypen, '
          f'{sum(len(v) for v in ENDPOINT_PARAMS.values())} Params, '
          f'{sum(len(v) for v in FILTERLISTE.values())} Filter')


def get_param(endpoint_code, param_name, default=None):
    """Gibt einen Endpoint-Parameter als String zurück."""
    return ENDPOINT_PARAMS.get(endpoint_code, {}).get(param_name, default)


def get_param_int(endpoint_code, param_name, default=0):
    """Gibt einen Endpoint-Parameter als Integer zurück."""
    val = get_param(endpoint_code, param_name)
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def get_filter_values(bereich):
    """Gibt die Liste der Werte für einen Filterbereich zurück."""
    return FILTERLISTE.get(bereich, [])


def get_filter_sql(bereich):
    """Gibt eine komma-separierte SQL-Liste der Filterwerte zurück."""
    values = get_filter_values(bereich)
    if not values:
        return "'__NONE__'"
    return ','.join(f"'{v}'" for v in values)


# ─── Initiales Laden ───
reload_config()
