"""Konfigurations-Service: Laedt Konfigurationstabellen aus MariaDB.

Stellt PK-Mapping, HSB-Config, Filter und Parameter als Modul-Variablen bereit.
Kann ueber reload_config() neu geladen werden.
"""

from studiengang_steckbriefe.services import mariadb_connector

# SQL-Platzhalter fuer leere IN-Listen (verhindert Syntaxfehler)
_SQL_NONE: str = "'__NONE__'"

# ═══════════════════════════════════════
# Fallback-Defaults (wenn DB leer ist)
# ═══════════════════════════════════════

_DEFAULT_HSB_CONFIG: dict[str, dict] = {
    "WM": {
        "hsb_code": "WM",
        "hsb_name": "Wirtschaft & Management",
        "icon": "💼",
        "farbe_hex": "#00534A",
        "sort_order": 1,
    },
    "GuS": {
        "hsb_code": "GuS",
        "hsb_name": "Gesundheit & Soziales",
        "icon": "🏥",
        "farbe_hex": "#6B1B4B",
        "sort_order": 2,
    },
    "WP": {
        "hsb_code": "WP",
        "hsb_name": "Wirtschaftspsychologie",
        "icon": "🧠",
        "farbe_hex": "#D04931",
        "sort_order": 3,
    },
    "IT": {
        "hsb_code": "IT",
        "hsb_name": "Informatik & Digitalisierung",
        "icon": "💻",
        "farbe_hex": "#00B3F0",
        "sort_order": 4,
    },
    "WR": {
        "hsb_code": "WR",
        "hsb_name": "Wirtschaftsrecht",
        "icon": "⚖️",
        "farbe_hex": "#D09910",
        "sort_order": 5,
    },
    "Ing": {
        "hsb_code": "Ing",
        "hsb_name": "Ingenieurwesen",
        "icon": "🔧",
        "farbe_hex": "#007C91",
        "sort_order": 6,
    },
}

_DEFAULT_HSB_EXCLUDE: list[str] = ["eufom BS", "OBS", ""]

_DEFAULT_EXCLUDED_HSZ: list[str] = ["Bangalore", "Pune", "Ahmedabad", "Sofia", "Venlo", "Luxemburg"]

_DEFAULT_FILTERLISTE: dict[str, list[str]] = {
    "HSB_EXCLUDE": ["eufom BS", "OBS", ""],
    "UE_RAUMID": ["274", "285", "349", "845", "1608"],
    "UE_VERANSTTYP": ["Sonderveranstaltung"],
    "UE_PRODUKTGRUPPE": ["Studium", "Akademische Weiterbildung"],
    "UE_STATUSRPL": ["A", "P"],
    "VERTIEFUNG_ART": ["Vertiefungsrichtung", "Wahlpflichtmodul", "Wahlmodul"],
    "VERTIEFUNG_FACH": ["General Studies Wahlmodul ZEUGNISSE", "Zusatzwahlfächer"],
    "LEISTUNGSART_IGNORE": ["Einschreibehindernispruefung", "Kooperation"],
    "ZUZAHLER_EMPF": ["Mitarbeiter"],
    "ZUZAHLER_KOSTENTYP": ["Arbeitgeber"],
    "DUAL_STUDIENFORMAT": ["ausbildungsintegrierend", "berufsintegrierend", "berufsbegleitend +"],
    "DUAL_BILDUNGSABSCHNITT": ["Erstausbildung"],
}

# ═══════════════════════════════════════
# Konfigurationsdaten (Modul-Level)
# ═══════════════════════════════════════

# PK-Mapping: alias_pk → basis_pk
PK_MAPPING: dict[str, str] = {}

# Reverse: basis_pk → [basis_pk, alias1, alias2, ...]
PK_REVERSE: dict[str, list[str]] = {}

# HSB-Config: hsb_code → {name, icon, farbe_hex, sort_order}
HSB_CONFIG: dict[str, dict] = {}

# HSB-Sortierung: hsb_code → sort_order
HSB_ORDER: dict[str, int] = {}

# Excluded Hochschulzentren
EXCLUDED_HSZ: list[str] = []
EXCLUDED_HSZ_SQL: str = _SQL_NONE

# Anrechnung-Regeln
ANRECHNUNG_REGELN: dict[str, list[dict]] = {}

# Endpoint-Parameter: {endpoint_code: {param_name: param_wert}}
ENDPOINT_PARAMS: dict[str, dict[str, str]] = {}

# Filterlisten: {bereich: [wert, ...]}
FILTERLISTE: dict[str, list[str]] = {}

# SQL CASE-Fragment fuer PK-Mapping
PK_CASE_SQL: str = ""

# Offene-Hochschule-Gruende
OFFENE_HOCHSCHULE_GRUENDE: list[str] = []
OFFENE_HOCHSCHULE_SQL: str = _SQL_NONE

# HSB-Exclude-Kuerzel
HSB_EXCLUDE_KUERZEL: list[str] = []
HSB_EXCLUDE_SQL: str = _SQL_NONE


def _build_pk_case_sql(alias: str = "l") -> str:
    """Generiert ein CASE WHEN ... END SQL-Fragment aus dem PK-Mapping."""
    if not PK_REVERSE:
        return f"{alias}.Produktkuerzel"
    cases = []
    for basis_pk, variants in PK_REVERSE.items():
        if len(variants) > 1:
            in_list = ",".join(f"'{v}'" for v in variants)
            cases.append(f"WHEN {alias}.Produktkuerzel IN ({in_list}) THEN '{basis_pk}'")
    if not cases:
        return f"{alias}.Produktkuerzel"
    return "CASE " + " ".join(cases) + f" ELSE {alias}.Produktkuerzel END"


def _build_pk_case_for_s() -> str:
    """Generiert CASE WHEN fuer Alias 's'."""
    return _build_pk_case_sql("s")


def _safe_query(sql: str) -> list[dict]:
    """Fuehrt eine MariaDB-Query aus. Gibt bei Verbindungsfehlern eine leere Liste zurueck."""
    try:
        return mariadb_connector.query(sql)
    except Exception as exc:
        print(f"[Config] MariaDB-Query fehlgeschlagen: {exc}")
        return []


def reload_config():
    """Laedt alle Konfigurations-Tabellen aus MariaDB neu.

    Bei Verbindungsfehlern werden Fallback-Defaults verwendet,
    damit die App auch ohne MariaDB-Zugriff starten kann.
    """
    global PK_MAPPING, PK_REVERSE, HSB_CONFIG, HSB_ORDER
    global EXCLUDED_HSZ, EXCLUDED_HSZ_SQL
    global ANRECHNUNG_REGELN, ENDPOINT_PARAMS, FILTERLISTE
    global PK_CASE_SQL, OFFENE_HOCHSCHULE_GRUENDE, OFFENE_HOCHSCHULE_SQL
    global HSB_EXCLUDE_KUERZEL, HSB_EXCLUDE_SQL

    print("[Config] Lade Konfiguration aus MariaDB...")

    # 1) Produktkuerzel-Alias
    rows = _safe_query("""
        SELECT a.AliasPk, sg.BasisPk
        FROM RpStudiengangSteckbriefeProduktKuerzelAlias a
        JOIN RpStudiengangSteckbriefeStudiengang sg ON sg.Id = a.StudiengangId
        WHERE a.IstAktiv = 1
    """)
    PK_MAPPING = {r["AliasPk"]: r["BasisPk"] for r in rows}

    # Reverse-Map
    PK_REVERSE = {}
    for alias_pk, basis_pk in PK_MAPPING.items():
        PK_REVERSE.setdefault(basis_pk, [basis_pk])
        if alias_pk not in PK_REVERSE[basis_pk]:
            PK_REVERSE[basis_pk].append(alias_pk)

    # 2) Hochschulbereiche
    rows = _safe_query(
        "SELECT HsbCode, Name, Icon, FarbeHex, Sortierung "
        "FROM RpStudiengangSteckbriefeHochschulbereich WHERE IstAktiv = 1"
    )
    HSB_CONFIG = {
        r["HsbCode"]: {
            "hsb_code": r["HsbCode"],
            "hsb_name": r["Name"],
            "icon": r["Icon"],
            "farbe_hex": r["FarbeHex"],
            "sort_order": r["Sortierung"],
        }
        for r in rows
    }
    if not HSB_CONFIG:
        HSB_CONFIG = dict(_DEFAULT_HSB_CONFIG)
        print("[Config] HSB_CONFIG leer – Fallback-Defaults werden verwendet.")
    HSB_ORDER = {code: cfg["sort_order"] for code, cfg in HSB_CONFIG.items()}

    # 3) Excluded Hochschulzentren
    rows = _safe_query(
        "SELECT Name FROM RpStudiengangSteckbriefeHochschulzentrum "
        "WHERE IstAusgeschlossen = 1 AND IstAktiv = 1"
    )
    EXCLUDED_HSZ = [r["Name"] for r in rows]
    if not EXCLUDED_HSZ:
        EXCLUDED_HSZ = list(_DEFAULT_EXCLUDED_HSZ)
        print("[Config] EXCLUDED_HSZ leer – Fallback-Defaults werden verwendet.")
    EXCLUDED_HSZ_SQL = ",".join(f"'{h}'" for h in EXCLUDED_HSZ) if EXCLUDED_HSZ else _SQL_NONE

    # 4) Anrechnung-Regeln
    rows = _safe_query(
        "SELECT Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet "
        "FROM RpStudiengangSteckbriefeAnrechnungRegel "
        "WHERE IstAktiv = 1 ORDER BY Prioritaet"
    )
    ANRECHNUNG_REGELN = {}
    for r in rows:
        ANRECHNUNG_REGELN.setdefault(r["Regeltyp"], []).append(
            {
                "regeltyp": r["Regeltyp"],
                "match_operator": r["AbgleichOperator"],
                "match_wert": r["AbgleichWert"],
                "kategorie": r["Kategorie"],
                "prioritaet": r["Prioritaet"],
            }
        )

    # Offene Hochschule
    OFFENE_HOCHSCHULE_GRUENDE = [
        r["match_wert"]
        for r in ANRECHNUNG_REGELN.get("ANRECHNUNGSGRUND", [])
        if r["kategorie"] == "OFFENE_HOCHSCHULE"
    ]
    OFFENE_HOCHSCHULE_SQL = (
        ",".join(f"'{g}'" for g in OFFENE_HOCHSCHULE_GRUENDE)
        if OFFENE_HOCHSCHULE_GRUENDE
        else _SQL_NONE
    )

    # 5) Endpoint-Parameter
    rows = _safe_query(
        "SELECT EndpunktCode, ParamName, ParamWert "
        "FROM RpStudiengangSteckbriefeEndpunktParameter WHERE IstAktiv = 1"
    )
    ENDPOINT_PARAMS = {}
    for r in rows:
        ENDPOINT_PARAMS.setdefault(r["EndpunktCode"], {})[r["ParamName"]] = r["ParamWert"]

    # 6) Filterliste
    rows = _safe_query(
        "SELECT Bereich, Wert, Typ FROM RpStudiengangSteckbriefeFilterliste WHERE IstAktiv = 1"
    )
    FILTERLISTE = {}
    for r in rows:
        FILTERLISTE.setdefault(r["Bereich"], []).append(r["Wert"])
    if not FILTERLISTE:
        FILTERLISTE = {k: list(v) for k, v in _DEFAULT_FILTERLISTE.items()}
        print("[Config] FILTERLISTE leer – Fallback-Defaults werden verwendet.")

    # HSB-Exclude
    HSB_EXCLUDE_KUERZEL = FILTERLISTE.get("HSB_EXCLUDE", [])
    if not HSB_EXCLUDE_KUERZEL:
        HSB_EXCLUDE_KUERZEL = list(_DEFAULT_HSB_EXCLUDE)
        print("[Config] HSB_EXCLUDE_KUERZEL leer – Fallback-Defaults werden verwendet.")
    HSB_EXCLUDE_SQL = (
        ",".join(f"'{k}'" for k in HSB_EXCLUDE_KUERZEL) if HSB_EXCLUDE_KUERZEL else _SQL_NONE
    )

    # 7) PK-CASE SQL-Fragmente
    PK_CASE_SQL = _build_pk_case_sql("l")

    print(
        f"[Config] Geladen: {len(PK_MAPPING)} Aliases, {len(HSB_CONFIG)} HSBs, "
        f"{len(EXCLUDED_HSZ)} excl. HSZ, {len(ANRECHNUNG_REGELN)} Regeltypen, "
        f"{sum(len(v) for v in ENDPOINT_PARAMS.values())} Params, "
        f"{sum(len(v) for v in FILTERLISTE.values())} Filter"
    )


def get_param(endpoint_code: str, param_name: str, default=None) -> str | None:
    """Gibt einen Endpoint-Parameter als String zurueck."""
    return ENDPOINT_PARAMS.get(endpoint_code, {}).get(param_name, default)


def get_param_int(endpoint_code: str, param_name: str, default: int = 0) -> int:
    """Gibt einen Endpoint-Parameter als Integer zurueck."""
    val = get_param(endpoint_code, param_name)
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def get_filter_values(bereich: str) -> list[str]:
    """Gibt die Liste der Werte fuer einen Filterbereich zurueck."""
    return FILTERLISTE.get(bereich, [])


def get_filter_sql(bereich: str) -> str:
    """Gibt eine komma-separierte SQL-Liste der Filterwerte zurueck."""
    values = get_filter_values(bereich)
    if not values:
        return _SQL_NONE
    return ",".join(f"'{v}'" for v in values)
