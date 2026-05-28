"""Konfigurations-Service: Laedt Konfigurationstabellen aus MariaDB.

Stellt PK-Mapping, HSB-Config, Filter und Parameter als Modul-Variablen bereit.
Kann ueber reload_config() neu geladen werden.
"""

from studiengang_steckbriefe.services import mariadb_connector

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
EXCLUDED_HSZ_SQL: str = ""

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
OFFENE_HOCHSCHULE_SQL: str = ""

# HSB-Exclude-Kuerzel
HSB_EXCLUDE_KUERZEL: list[str] = []
HSB_EXCLUDE_SQL: str = ""


def _build_pk_case_sql(alias: str = "l") -> str:
    """Generiert ein CASE WHEN ... END SQL-Fragment aus dem PK-Mapping."""
    if not PK_REVERSE:
        return f"{alias}.Produktkuerzel"
    cases = []
    for basis_pk, variants in PK_REVERSE.items():
        if len(variants) > 1:
            in_list = ",".join(f"'{v}'" for v in variants)
            cases.append(
                f"WHEN {alias}.Produktkuerzel IN ({in_list}) THEN '{basis_pk}'"
            )
    if not cases:
        return f"{alias}.Produktkuerzel"
    return "CASE " + " ".join(cases) + f" ELSE {alias}.Produktkuerzel END"


def _build_pk_case_for_s() -> str:
    """Generiert CASE WHEN fuer Alias 's'."""
    return _build_pk_case_sql("s")


def reload_config():
    """Laedt alle Konfigurations-Tabellen aus MariaDB neu."""
    global PK_MAPPING, PK_REVERSE, HSB_CONFIG, HSB_ORDER
    global EXCLUDED_HSZ, EXCLUDED_HSZ_SQL
    global ANRECHNUNG_REGELN, ENDPOINT_PARAMS, FILTERLISTE
    global PK_CASE_SQL, OFFENE_HOCHSCHULE_GRUENDE, OFFENE_HOCHSCHULE_SQL
    global HSB_EXCLUDE_KUERZEL, HSB_EXCLUDE_SQL

    print("[Config] Lade Konfiguration aus MariaDB...")

    # 1) Produktkuerzel-Alias
    rows = mariadb_connector.query("""
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
    rows = mariadb_connector.query(
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
    HSB_ORDER = {r["HsbCode"]: r["Sortierung"] for r in rows}

    # 3) Excluded Hochschulzentren
    rows = mariadb_connector.query(
        "SELECT Name FROM RpStudiengangSteckbriefeHochschulzentrum "
        "WHERE IstAusgeschlossen = 1 AND IstAktiv = 1"
    )
    EXCLUDED_HSZ = [r["Name"] for r in rows]
    EXCLUDED_HSZ_SQL = (
        ",".join(f"'{h}'" for h in EXCLUDED_HSZ) if EXCLUDED_HSZ else "'__NONE__'"
    )

    # 4) Anrechnung-Regeln
    rows = mariadb_connector.query(
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
        else "'__NONE__'"
    )

    # 5) Endpoint-Parameter
    rows = mariadb_connector.query(
        "SELECT EndpunktCode, ParamName, ParamWert "
        "FROM RpStudiengangSteckbriefeEndpunktParameter WHERE IstAktiv = 1"
    )
    ENDPOINT_PARAMS = {}
    for r in rows:
        ENDPOINT_PARAMS.setdefault(r["EndpunktCode"], {})[r["ParamName"]] = r[
            "ParamWert"
        ]

    # 6) Filterliste
    rows = mariadb_connector.query(
        "SELECT Bereich, Wert, Typ FROM RpStudiengangSteckbriefeFilterliste WHERE IstAktiv = 1"
    )
    FILTERLISTE = {}
    for r in rows:
        FILTERLISTE.setdefault(r["Bereich"], []).append(r["Wert"])

    # HSB-Exclude
    HSB_EXCLUDE_KUERZEL = FILTERLISTE.get("HSB_EXCLUDE", [])
    HSB_EXCLUDE_SQL = (
        ",".join(f"'{k}'" for k in HSB_EXCLUDE_KUERZEL)
        if HSB_EXCLUDE_KUERZEL
        else "'__NONE__'"
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
        return "'__NONE__'"
    return ",".join(f"'{v}'" for v in values)
