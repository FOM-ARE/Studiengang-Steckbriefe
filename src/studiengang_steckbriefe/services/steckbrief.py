"""Service-Schicht fuer Studiengang-Steckbriefe.

Enthaelt die gesamte Fachlogik fuer alle Steckbrief-Endpoints.
Jede oeffentliche Funktion entspricht einem API-Endpoint.
"""

from __future__ import annotations

import re
from datetime import date

from studiengang_steckbriefe.services import config_db, queries
from studiengang_steckbriefe.services.cache import cache_get, cache_set
from studiengang_steckbriefe.services.db_connector import query_db, query_db_multi

# ===================================================================
# Hilfsfunktionen
# ===================================================================


def expand_pk(produktkuerzel: str) -> list[str]:
    """Gibt Liste aller Produktkuerzel-Varianten fuer ein Basis-PK zurueck."""
    return config_db.PK_REVERSE.get(produktkuerzel, [produktkuerzel])


def pk_in_clause(produktkuerzel: str) -> tuple[str, list[str]]:
    """Gibt (sql_fragment, params) fuer IN-Clause zurueck."""
    variants = expand_pk(produktkuerzel)
    placeholders = ",".join("?" * len(variants))
    return f"IN ({placeholders})", variants


def pk_expand_sql(sql: str, produktkuerzel: str, count: int | None = None) -> tuple[str, list[str]]:
    """Ersetzt alle '= ?' Produktkuerzel-Filter durch 'IN (?,?,...)'.

    Args:
        sql: SQL-String mit '= ?' Platzhaltern.
        produktkuerzel: Basis-Produktkuerzel.
        count: Anzahl der '= ?'-Stellen die ersetzt werden (None = alle).

    Returns:
        Tuple aus (neues_sql, params_liste).
    """
    variants = expand_pk(produktkuerzel)
    placeholders = ",".join("?" * len(variants))
    in_clause = f"IN ({placeholders})"
    new_sql = sql
    params: list[str] = []
    replaced = 0
    while "= ?" in new_sql:
        if count is not None and replaced >= count:
            break
        new_sql = new_sql.replace("= ?", in_clause, 1)
        params.extend(variants)
        replaced += 1
    return new_sql, params


def _aktuelles_semester() -> str:
    """Gibt das aktuelle Semesterkuerzel im DB-Format zurueck (z.B. '2026-SS')."""
    today = date.today()
    return f"{today.year}-SS" if 3 <= today.month <= 8 else f"{today.year}-WS"


def _semester_filter_7(rows: list[dict], key: str = "Semesterkuerzel") -> list[dict]:
    """Filtert Zeilen auf aktuelles Semester + letzte 6 (max 7 Semester)."""
    cur = _aktuelles_semester()
    filtered = [r for r in rows if r[key] <= cur]
    unique_sems = sorted(set(r[key] for r in filtered))[-7:]
    sem_set = set(unique_sems)
    return [r for r in filtered if r[key] in sem_set]


def _fmt_sem(sk: str) -> str:
    """Formatiert Semesterkuerzel: '2024-WS' -> 'WS-2024'."""
    if not sk:
        return "?"
    return f"{'WS' if sk.endswith('WS') else 'SS'}-{sk[:4]}"


# ===================================================================
# studiengaenge
# ===================================================================


_SG_BUSINESS_ADMINISTRATION = "Business Administration"
_NAME_MAPPING = {
    "Business Administration - Healthcare Management": _SG_BUSINESS_ADMINISTRATION,
    "Business Administration - dual kompakt": _SG_BUSINESS_ADMINISTRATION,
    "Business Administration Vertiefung Public Management": _SG_BUSINESS_ADMINISTRATION,
    "Business Administration, Vertiefung Public Management": _SG_BUSINESS_ADMINISTRATION,
    "Business Administration - Public Management": _SG_BUSINESS_ADMINISTRATION,
    "Business Administration \u2013 Versicherungsbetrieb": _SG_BUSINESS_ADMINISTRATION,
    "Business Administration \u2013 Versicherungsvertrieb": _SG_BUSINESS_ADMINISTRATION,
    "Engineering & Management": "Wirtschaftsingenieurwesen",
    "Prim\u00e4rmedizinisches Versorgungs- und Praxismanagement": "Primary Care Management",
    "Soziale Arbeit - kommunal": "Soziale Arbeit",
    "Soziale Arbeit \u2013 kommunal": "Soziale Arbeit",
    "Wirtschaftsinformatik \u2013 kommunal": "Wirtschaftsinformatik",
    "Wirtschaftsinformatik - kommunal": "Wirtschaftsinformatik",
}


def _merge_studierende(stud_map: dict[str, int]) -> dict[str, int]:
    """Rechnet Studierende-Map auf zusammengefasste PKs um."""
    merged: dict[str, int] = {}
    pk_mapping = config_db.PK_MAPPING
    for pk, count in stud_map.items():
        merged_pk = pk_mapping.get(pk, pk)
        merged[merged_pk] = merged.get(merged_pk, 0) + count
    return merged


def _build_sg_map(rows: list[dict]) -> dict[str, dict]:
    """Dedupliziert und fasst Studiengaenge zusammen."""
    pk_mapping = config_db.PK_MAPPING
    sg_map: dict[str, dict] = {}
    for r in rows:
        raw_pk = r["Produktkuerzel"]
        pk = pk_mapping.get(raw_pk, raw_pk)
        sg_name = r["Studiengang"] or ""
        name_match = re.match(r"^(.+?)\s*\([^)]+\)\s*$", sg_name)
        base_name = name_match.group(1).strip() if name_match else sg_name
        base_name = _NAME_MAPPING.get(base_name, base_name)
        display_name = f"{base_name} ({pk})"
        if pk not in sg_map or len(display_name) < len(sg_map[pk]["Studiengang"]):
            sg_map[pk] = {
                "Produktkuerzel": pk,
                "Studiengang": display_name,
                "Hochschulbereich": r["Hochschulbereich"],
                "HochschulbereichKuerzel": r["HochschulbereichKuerzel"],
                "Abschluss": r.get("Abschluss") or ("Master" if pk.startswith("M") else "Bachelor"),
            }
    return sg_map


def _build_hsb_map(sg_map: dict[str, dict], stud_map: dict[str, int]) -> dict[str, dict]:
    """Gruppiert Studiengaenge nach Hochschulbereich."""
    hsb_map: dict[str, dict] = {}
    for pk, r in sg_map.items():
        hsb_kuerzel = r["HochschulbereichKuerzel"]
        if not hsb_kuerzel:
            continue
        if hsb_kuerzel not in hsb_map:
            hsb_cfg = config_db.HSB_CONFIG.get(hsb_kuerzel, {})
            hsb_map[hsb_kuerzel] = {
                "id": hsb_kuerzel.lower().replace(" ", "_"),
                "name": r["Hochschulbereich"],
                "kuerzel": hsb_kuerzel,
                "icon": hsb_cfg.get("icon", "\ud83d\udcda"),
                "farbe": hsb_cfg.get("farbe_hex", "#607D8B"),
                "programmes": [],
            }
        abschluss_raw = r.get("Abschluss") or ("Master" if pk.startswith("M") else "Bachelor")
        abschluss_kurz = "Master" if "master" in abschluss_raw.lower() else "Bachelor"
        hsb_map[hsb_kuerzel]["programmes"].append(
            {
                "id": f"{hsb_kuerzel}_{abschluss_kurz[:1]}A_{pk}",
                "name": r["Studiengang"],
                "kurzname": pk,
                "abschluss": abschluss_raw,
                "studierende_gesamt": stud_map.get(pk, 0),
            }
        )
    return hsb_map


def get_studiengaenge() -> list[dict]:
    """Laedt die Liste aller Studiengaenge mit Studierendenzahlen.

    Returns:
        Liste von Hochschulbereichen mit ihren Studiengaengen.
    """
    cached = cache_get("studiengaenge")
    if cached:
        return cached

    rows = query_db(queries.SQL_STUDIENGAENGE_LISTE)
    stud_rows = query_db(queries.SQL_STUDIERENDE_AKTUELL)
    stud_map = {r["Produktkuerzel"]: int(r["Gesamtstudierende"]) for r in stud_rows}

    merged_stud = _merge_studierende(stud_map)
    sg_map = _build_sg_map(rows)
    hsb_map = _build_hsb_map(sg_map, merged_stud)

    for hsb in hsb_map.values():
        hsb["programmes"].sort(key=lambda p: p["name"])

    HSB_ORDER = config_db.HSB_ORDER
    data = sorted(hsb_map.values(), key=lambda h: HSB_ORDER.get(h["kuerzel"], 99))
    cache_set("studiengaenge", data)
    return data


# ===================================================================
# trends
# ===================================================================


def _build_zeitreihe(rows: list[dict], jahre: list) -> tuple:
    """Baut Zeitreihen-Listen fuer SS und WS aus den Rohdaten."""
    zeitreihe_ss, zeitreihe_ws = [], []
    fom_avg_ss, fom_avg_ws = [], []
    beginner_ss, beginner_ws = [], []
    beginner_fom_avg_ss, beginner_fom_avg_ws = [], []

    for jahr in jahre:
        ss = next((r for r in rows if r["Jahr"] == jahr and r["SemesterTyp"] == "SS"), None)
        ws = next((r for r in rows if r["Jahr"] == jahr and r["SemesterTyp"] == "WS"), None)

        zeitreihe_ss.append(int(ss["Gesamtstudierende_SG"]) if ss else 0)
        zeitreihe_ws.append(int(ws["Gesamtstudierende_SG"]) if ws else 0)
        fom_avg_ss.append(round(float(ss["Gesamtstudierende_FOM_Avg"])) if ss else 0)
        fom_avg_ws.append(round(float(ws["Gesamtstudierende_FOM_Avg"])) if ws else 0)
        beginner_ss.append(int(ss["Beginner_SG"]) if ss else 0)
        beginner_ws.append(int(ws["Beginner_SG"]) if ws else 0)
        beginner_fom_avg_ss.append(round(float(ss["Beginner_FOM_Avg"])) if ss else 0)
        beginner_fom_avg_ws.append(round(float(ws["Beginner_FOM_Avg"])) if ws else 0)

    return (
        zeitreihe_ss, zeitreihe_ws,
        fom_avg_ss, fom_avg_ws,
        beginner_ss, beginner_ws,
        beginner_fom_avg_ss, beginner_fom_avg_ws,
    )


def _calc_delta_str(zeitreihe_ss: list, zeitreihe_ws: list) -> tuple[int, str]:
    """Berechnet aktuellen Wert und Delta-String fuer Gesamtstudierende."""
    if zeitreihe_ws and zeitreihe_ws[0]:
        aktuell = zeitreihe_ws[0]
        vorher = zeitreihe_ws[1] if len(zeitreihe_ws) >= 2 else 0
    else:
        aktuell = zeitreihe_ss[0] if zeitreihe_ss else 0
        vorher = zeitreihe_ss[1] if len(zeitreihe_ss) >= 2 else 0
    diff = aktuell - vorher
    pct = f"{(diff / vorher * 100):.1f}".replace(".", ",") if vorher else "0,0"
    sign = "+" if diff >= 0 else ""
    return aktuell, f"{sign}{diff} ({sign}{pct}%)"


def _calc_beginner_delta(beginner_ss: list, beginner_ws: list) -> tuple[int, str]:
    """Berechnet aktuellen Wert und Delta-String fuer Studienbeginner."""
    b_ss_aktuell = beginner_ss[0] if beginner_ss else 0
    b_ss_vorher = beginner_ss[1] if len(beginner_ss) >= 2 else 0
    b_ws_aktuell = beginner_ws[0] if beginner_ws else 0
    b_ws_vorher = beginner_ws[1] if len(beginner_ws) >= 2 else 0
    if b_ws_aktuell:
        b_aktuell = b_ws_aktuell + b_ss_aktuell
        b_vorher = b_ws_vorher + b_ss_vorher
    else:
        b_aktuell = b_ss_aktuell
        b_vorher = b_ss_vorher
    b_diff = b_aktuell - b_vorher
    b_pct = f"{(b_diff / b_vorher * 100):.1f}".replace(".", ",") if b_vorher else "0,0"
    b_sign = "+" if b_diff >= 0 else ""
    return b_aktuell, f"{b_sign}{b_diff} ({b_sign}{b_pct}%)"


def _build_hsz_data(hsz_rows: list[dict], hsz_avg_rows: list[dict]) -> dict:
    """Baut das HSZ-Detail-Dict aus Studierenden- und Durchschnittsdaten."""
    hsz_data: dict = {}
    for r in hsz_rows:
        hsz = r["Hochschulzentrum"]
        jahr = r["Jahr"]
        if hsz not in hsz_data:
            hsz_data[hsz] = {}
        if jahr not in hsz_data[hsz]:
            hsz_data[hsz][jahr] = {
                "ss": 0, "ws": 0,
                "beginner_ss": 0, "beginner_ws": 0,
                "avg_ss": 0, "avg_ws": 0,
                "avg_beginner_ss": 0, "avg_beginner_ws": 0,
            }
        if r["SemesterTyp"] == "SS":
            hsz_data[hsz][jahr]["ss"] = int(r["Gesamtstudierende"])
            hsz_data[hsz][jahr]["beginner_ss"] = int(r["Beginner"])
        else:
            hsz_data[hsz][jahr]["ws"] = int(r["Gesamtstudierende"])
            hsz_data[hsz][jahr]["beginner_ws"] = int(r["Beginner"])

    for r in hsz_avg_rows:
        hsz = r["Hochschulzentrum"]
        jahr = r["Jahr"]
        if hsz not in hsz_data or jahr not in hsz_data[hsz]:
            continue
        if r["SemesterTyp"] == "SS":
            hsz_data[hsz][jahr]["avg_ss"] = (
                round(float(r["AvgStudierende"])) if r["AvgStudierende"] else 0
            )
            hsz_data[hsz][jahr]["avg_beginner_ss"] = (
                round(float(r["AvgBeginner"])) if r["AvgBeginner"] else 0
            )
        else:
            hsz_data[hsz][jahr]["avg_ws"] = (
                round(float(r["AvgStudierende"])) if r["AvgStudierende"] else 0
            )
            hsz_data[hsz][jahr]["avg_beginner_ws"] = (
                round(float(r["AvgBeginner"])) if r["AvgBeginner"] else 0
            )
    return hsz_data


def get_trends(produktkuerzel: str) -> dict:
    """Berechnet Studierenden-Trends (Zeitreihe, HSZ-Detail).

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Zeitreihen-Daten und HSZ-Detail.
    """
    cache_key = f"trends_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_zr, params_zr = pk_expand_sql(queries.SQL_STUDIERENDE_ZEITREIHE, produktkuerzel)
    sql_hsz, params_hsz = pk_expand_sql(queries.SQL_STUDIERENDE_HSZ, produktkuerzel)
    rows, hsz_rows, hsz_avg_rows = query_db_multi(
        [
            (sql_zr, params_zr),
            (sql_hsz, params_hsz),
            (queries.SQL_STUDIERENDE_HSZ_AVG, []),
        ]
    )

    rows = _semester_filter_7(rows)
    hsz_rows = _semester_filter_7(hsz_rows)
    hsz_avg_rows = _semester_filter_7(hsz_avg_rows)

    jahre = sorted(set(r["Jahr"] for r in rows), reverse=True)

    (
        zeitreihe_ss, zeitreihe_ws,
        fom_avg_ss, fom_avg_ws,
        beginner_ss, beginner_ws,
        beginner_fom_avg_ss, beginner_fom_avg_ws,
    ) = _build_zeitreihe(rows, jahre)

    aktuell, delta_str = _calc_delta_str(zeitreihe_ss, zeitreihe_ws)
    b_aktuell, b_delta = _calc_beginner_delta(beginner_ss, beginner_ws)
    hsz_data = _build_hsz_data(hsz_rows, hsz_avg_rows)

    data = {
        "studierende_gesamt": aktuell,
        "studierende_delta": delta_str,
        "studienbeginner": b_aktuell,
        "studienbeginner_delta": b_delta,
        "zeitreihe_semester": jahre,
        "zeitreihe_ss": zeitreihe_ss,
        "zeitreihe_ws": zeitreihe_ws,
        "zeitreihe_fom_avg_ss": fom_avg_ss,
        "zeitreihe_fom_avg_ws": fom_avg_ws,
        "studienbeginner_zeitreihe_semester": jahre,
        "studienbeginner_zeitreihe_ss": beginner_ss,
        "studienbeginner_zeitreihe_ws": beginner_ws,
        "studienbeginner_zeitreihe_fom_avg_ss": beginner_fom_avg_ss,
        "studienbeginner_zeitreihe_fom_avg_ws": beginner_fom_avg_ws,
        "hsz_detail": hsz_data,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# aktive HSZen
# ===================================================================


def get_aktive_hszen(produktkuerzel: str) -> list[str]:
    """Gibt die aktiven Hochschulzentren fuer einen Studiengang zurueck."""
    cache_key = f"hszen_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    sql_hszen, params_hszen = pk_expand_sql(queries.SQL_AKTIVE_HSZEN, produktkuerzel)
    rows = query_db(sql_hszen, params_hszen)
    data = [r["Hochschulzentrum"] for r in rows]
    cache_set(cache_key, data)
    return data


# ===================================================================
# stammdaten
# ===================================================================


def _pct(val, total) -> float:
    return round(int(val or 0) / max(int(total or 0), 1) * 100, 1)


def _detail_block(r: dict | None) -> tuple:
    """Berechnet Prozentwerte fuer Geschlecht, Staatsangehoerigkeit, Dual und OffeneHS."""
    if not r:
        return (
            {"weiblich": 0, "maennlich": 0},
            {"inlaendisch": 0, "auslaendisch": 0, "dueh": 0},
            {"dual": 0, "tagesstudium": 0, "nein": 0},
            {"ja": 0, "nein": 0},
        )
    t = int(r["Total"] or 1)
    geschlecht = {"weiblich": _pct(r["Weiblich"], t), "maennlich": _pct(r["Maennlich"], t)}
    inl = int(r.get("Inlaendisch", 0) or 0)
    ausl = int(r.get("Auslaendisch", 0) or 0)
    unbek = int(r.get("Unbekannt", 0) or 0)
    staatsang = {"inlaendisch": _pct(inl, t), "auslaendisch": _pct(ausl, t), "dueh": _pct(unbek, t)}
    dual_v = int(r.get("Dual", 0) or 0)
    tages = int(r.get("Tagesstudium", 0) or 0)
    dual = {"dual": _pct(dual_v, t), "tagesstudium": _pct(tages, t), "nein": _pct(t - dual_v - tages, t)}
    offene_v = int(r.get("OffeneHochschule", 0) or 0)
    intern = {"ja": _pct(offene_v, t), "nein": _pct(t - offene_v, t)}
    return geschlecht, staatsang, dual, intern


def _sum_detail_rows(rows_list: list) -> dict | None:
    """Aggregiert Detail-Zeilen ueber alle HSZ."""
    if not rows_list:
        return None
    agg = {"Total": 0, "Weiblich": 0, "Maennlich": 0, "Inlaendisch": 0,
           "Auslaendisch": 0, "Unbekannt": 0, "Dual": 0, "Tagesstudium": 0, "OffeneHochschule": 0}
    for r in rows_list:
        for k in agg:
            agg[k] += int(r.get(k, 0) or 0)
    return agg


def _weighted_alter_zeitreihe(alter_rows: list) -> tuple[list, list]:
    """Berechnet gewichteten Altersdurchschnitt je Semester."""
    sem_alter: dict = {}
    for r in alter_rows:
        sk = r["Semesterkuerzel"]
        avg_val = float(r["DurchschnittsAlter"]) if r["DurchschnittsAlter"] else None
        cnt = int(r["Cnt"] or 0)
        if avg_val is not None and cnt > 0:
            sem_alter.setdefault(sk, {"sum": 0, "cnt": 0})
            sem_alter[sk]["sum"] += avg_val * cnt
            sem_alter[sk]["cnt"] += cnt
    overall = [
        {"Semesterkuerzel": sk, "DurchschnittsAlter": d["sum"] / d["cnt"]}
        for sk, d in sorted(sem_alter.items()) if d["cnt"] > 0
    ]
    filtered = _semester_filter_7(overall)
    return (
        [_fmt_sem(r["Semesterkuerzel"]) for r in filtered],
        [round(float(r["DurchschnittsAlter"]), 1) for r in filtered],
    )


def _aggregate_beruf(beruf_rows: list, zeitraum: str) -> tuple[list, int]:
    """Aggregiert Berufsausbildungs-Daten fuer einen Zeitraum."""
    agg: dict = {}
    for r in beruf_rows:
        if r["Zeitraum"] == zeitraum:
            ba = r["Berufsausbildung"]
            agg[ba] = agg.get(ba, 0) + int(r["Cnt"])
    result = sorted(agg.items(), key=lambda x: -x[1])
    return result, sum(v for _, v in result) or 1


def _build_hsz_stammdaten(
    hsz: str, alter_rows: list, detail_rows: list, beruf_rows: list, all_sv: list
) -> dict:
    """Berechnet Stammdaten-Block fuer ein einzelnes HSZ."""
    h_alter_filtered = _semester_filter_7([r for r in alter_rows if r.get("HSZ") == hsz])
    h_aktuell = _sum_detail_rows([r for r in detail_rows if r["Zeitraum"] == "aktuell" and r.get("HSZ") == hsz])
    h_rest = _sum_detail_rows([r for r in detail_rows if r["Zeitraum"] == "rest" and r.get("HSZ") == hsz])
    h_g_akt, h_s_akt, h_d_akt, h_i_akt = _detail_block(h_aktuell)
    h_g_rest, h_s_rest, h_d_rest, h_i_rest = _detail_block(h_rest)
    h_beruf_akt, h_total_akt = _aggregate_beruf(beruf_rows, "aktuell")
    h_beruf_rest, h_total_rest = _aggregate_beruf(
        [r for r in beruf_rows if r.get("HSZ") == hsz], "rest"
    )
    h_beruf_akt = sorted(
        [(r["Berufsausbildung"], int(r["Cnt"])) for r in beruf_rows
         if r["Zeitraum"] == "aktuell" and r.get("HSZ") == hsz],
        key=lambda x: -x[1],
    )
    h_beruf_rest = sorted(
        [(r["Berufsausbildung"], int(r["Cnt"])) for r in beruf_rows
         if r["Zeitraum"] == "rest" and r.get("HSZ") == hsz],
        key=lambda x: -x[1],
    )
    h_total_akt = sum(cnt for _, cnt in h_beruf_akt) or 1
    h_total_rest = sum(cnt for _, cnt in h_beruf_rest) or 1
    return {
        "alter_zeitreihe_semester": [_fmt_sem(r["Semesterkuerzel"]) for r in h_alter_filtered],
        "alter_zeitreihe": [
            round(float(r["DurchschnittsAlter"]), 1) if r["DurchschnittsAlter"] else None
            for r in h_alter_filtered
        ],
        "top_berufsausbildungen_aktuell": [
            {"name": ba, "pct": round(cnt / h_total_akt * 100, 1)} for ba, cnt in h_beruf_akt[:5]
        ],
        "top_berufsausbildungen_rest": [
            {"name": ba, "pct": round(cnt / h_total_rest * 100, 1)} for ba, cnt in h_beruf_rest[:5]
        ],
        "geschlecht_aktuell": h_g_akt, "geschlecht_rest": h_g_rest,
        "staatsang_aktuell": h_s_akt, "staatsang_rest": h_s_rest,
        "dual_aktuell": h_d_akt, "dual_rest": h_d_rest,
        "intern_aktuell": h_i_akt, "intern_rest": h_i_rest,
    }


def get_stammdaten(produktkuerzel: str) -> dict:
    """Berechnet Stammdaten (Alter, Geschlecht, Staatsangehoerigkeit, Dual, Beruf).

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Stammdaten-Auswertungen.
    """
    cache_key = f"stammdaten_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_alter, p_alter = pk_expand_sql(queries.SQL_STAMMDATEN_ALTER, produktkuerzel)
    sql_detail, p_detail = pk_expand_sql(queries.SQL_STAMMDATEN_DETAIL, produktkuerzel)
    sql_beruf_a, p_beruf_a = pk_expand_sql(queries.SQL_STAMMDATEN_BERUFSAUSBILDUNG, produktkuerzel)
    alter_rows, detail_rows, beruf_rows = query_db_multi(
        [(sql_alter, p_alter), (sql_detail, p_detail), (sql_beruf_a, p_beruf_a)]
    )

    alter_semester, alter_werte = _weighted_alter_zeitreihe(alter_rows)

    aktuell = _sum_detail_rows([r for r in detail_rows if r["Zeitraum"] == "aktuell"])
    rest = _sum_detail_rows([r for r in detail_rows if r["Zeitraum"] == "rest"])
    g_akt, s_akt, d_akt, i_akt = _detail_block(aktuell)
    g_rest, s_rest, d_rest, i_rest = _detail_block(rest)

    beruf_akt_raw, total_akt = _aggregate_beruf(beruf_rows, "aktuell")
    beruf_rest_raw, total_rest = _aggregate_beruf(beruf_rows, "rest")

    hsz_set_s = sorted(
        set(r.get("HSZ") for r in alter_rows if r.get("HSZ"))
        | set(r.get("HSZ") for r in detail_rows if r.get("HSZ"))
    )
    hsz_detail = {
        hsz: _build_hsz_stammdaten(hsz, alter_rows, detail_rows, beruf_rows, [])
        for hsz in hsz_set_s
    }

    data = {
        "alter_zeitreihe_semester": alter_semester,
        "alter_zeitreihe": alter_werte,
        "top_berufsausbildungen_aktuell": [
            {"name": ba, "pct": round(cnt / total_akt * 100, 1)} for ba, cnt in beruf_akt_raw[:5]
        ],
        "top_berufsausbildungen_rest": [
            {"name": ba, "pct": round(cnt / total_rest * 100, 1)} for ba, cnt in beruf_rest_raw[:5]
        ],
        "geschlecht_aktuell": g_akt, "geschlecht_rest": g_rest,
        "staatsang_aktuell": s_akt, "staatsang_rest": s_rest,
        "dual_aktuell": d_akt, "dual_rest": d_rest,
        "intern_aktuell": i_akt, "intern_rest": i_rest,
        "hsz_detail": hsz_detail,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# studienerfolg
# ===================================================================


def _sem_sort_key(x: str) -> int:
    return 99 if x == "9+" else int(x)


def _calc_cluster_total(pivot: dict, labels_num: list, name: str, rsz_filter: int | None) -> int:
    t = 0
    for lbl in labels_num:
        cd = pivot.get(lbl, {}).get(name, {})
        t += cd.get(rsz_filter, 0) if rsz_filter is not None else sum(cd.values())
    return t


def _calc_fachsem_pct(rows: list, labels_num: list) -> list:
    """Berechnet Fachsemester-Prozentwerte (Abbrecher, Wechsler, Eingeschrieben, Absolvent)."""
    pivot: dict = {}
    for r in rows:
        fs = r["Fachsem"]
        if fs == "0":
            continue
        cluster = r["AusstiegsCluster"]
        if cluster is None:
            continue
        rsz = int(r["RSZ"])
        pivot.setdefault(fs, {}).setdefault(cluster, {})
        pivot[fs][cluster][rsz] = pivot[fs][cluster].get(rsz, 0) + int(r["Anzahl"])

    kohortengroesse = (
        sum(sum(sum(rv.values()) for rv in cv.values()) for cv in pivot.values()) or 1
    )

    result = []
    for lbl in labels_num:
        abbrecher_fs = sum(pivot.get(lbl, {}).get("Abbrecher", {}).values())
        result.append(round(abbrecher_fs / kohortengroesse * 100, 1))

    for cluster, rsz_filter in [
        ("Abbrecher", None), ("Wechsler", None),
        ("Eingeschrieben", 0), ("Eingeschrieben", 1), ("Absolvent", None),
    ]:
        total = _calc_cluster_total(pivot, labels_num, cluster, rsz_filter)
        result.append(round(total / kohortengroesse * 100, 1))
    return result


def _calc_verlaengerung(rows: list) -> dict:
    """Pivotiert Verlängerungssemester-Daten."""
    pivot: dict = {}
    for r in rows:
        sv = max(int(r["VerlaengerungsSem"]), 0)
        key = "9+" if sv > 8 else str(sv)
        pivot[key] = pivot.get(key, 0) + int(r["Anzahl"])
    return pivot


def _aggregate_fs_sg(fs_sg: list) -> list:
    """Aggregiert Fachsemester-Daten ueber alle HSZ."""
    agg: dict = {}
    for r in fs_sg:
        key = (r["Fachsem"], r["AusstiegsCluster"], int(r["RSZ"]))
        agg[key] = agg.get(key, 0) + int(r["Anzahl"])
    return [{"Fachsem": k[0], "AusstiegsCluster": k[1], "RSZ": k[2], "Anzahl": v}
            for k, v in agg.items()]


def get_studienerfolg(produktkuerzel: str) -> dict:
    """Berechnet Fachsemester-Verteilung und Verlaengerungssemester.

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Fachsemester- und Verlaengerungs-Daten.
    """
    cache_key = f"studienerfolg_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    fs_fom = cache_get("_global_fachsemester_fom")
    if not fs_fom:
        fs_fom = query_db(queries.SQL_FACHSEMESTER_FOM)
        cache_set("_global_fachsemester_fom", fs_fom)
    vl_fom = cache_get("_global_verlaengerung_fom")
    if not vl_fom:
        vl_fom = query_db(queries.SQL_VERLAENGERUNG_FOM)
        cache_set("_global_verlaengerung_fom", vl_fom)

    sql_fs, p_fs = pk_expand_sql(queries.SQL_FACHSEMESTER, produktkuerzel)
    sql_vl, p_vl = pk_expand_sql(queries.SQL_VERLAENGERUNG, produktkuerzel)
    fs_sg, vl_sg = query_db_multi([(sql_fs, p_fs), (sql_vl, p_vl)])

    fs_labels_num = sorted(
        set(r["Fachsem"] for r in fs_sg if r["Fachsem"] not in ("0",)),
        key=_sem_sort_key,
    )
    fs_labels = [f"{lbl}. FS" if lbl != "9+" else "9+" for lbl in fs_labels_num] + [
        "Abbrecher", "Wechsler", "aktiv\n(regulaer)", "aktiv\n(Verlaengerung)", "Absolventen",
    ]

    fs_sg_overall = _aggregate_fs_sg(fs_sg)
    sg_pcts = _calc_fachsem_pct(fs_sg_overall, fs_labels_num)
    fom_pcts = _calc_fachsem_pct(fs_fom, fs_labels_num)

    vl_sg_pivot = _calc_verlaengerung(vl_sg)
    vl_fom_pivot = _calc_verlaengerung(vl_fom)
    all_sv = sorted(set(list(vl_sg_pivot.keys()) + list(vl_fom_pivot.keys())), key=_sem_sort_key)
    vl_labels = [
        "Regelstudienzeit" if sv == "0" else (f"{sv} VS" if sv == "9+" else f"{sv}. VS")
        for sv in all_sv
    ]
    vl_sg_vals = [vl_sg_pivot.get(sv, 0) for sv in all_sv]
    vl_fom_vals = [vl_fom_pivot.get(sv, 0) for sv in all_sv]
    vl_pct = [
        round(vl_sg_pivot.get(sv, 0) / max(vl_fom_pivot.get(sv, 0), 1) * 100, 1) for sv in all_sv
    ]

    hsz_set_se = sorted(
        set(r.get("HSZ") for r in fs_sg if r.get("HSZ"))
        | set(r.get("HSZ") for r in vl_sg if r.get("HSZ"))
    )
    hsz_detail = {
        hsz: {
            "fachsemester_sg": _calc_fachsem_pct(
                [r for r in fs_sg if r.get("HSZ") == hsz], fs_labels_num
            ),
            "verlaengerung_sg": [
                _calc_verlaengerung([r for r in vl_sg if r.get("HSZ") == hsz]).get(sv, 0)
                for sv in all_sv
            ],
        }
        for hsz in hsz_set_se
    }

    data = {
        "fachsemester_labels": fs_labels,
        "fachsemester_sg": sg_pcts,
        "fachsemester_fom": fom_pcts,
        "verlaengerung_labels": vl_labels,
        "verlaengerung_fom": vl_fom_vals,
        "verlaengerung_sg": vl_sg_vals,
        "verlaengerung_pct": vl_pct,
        "hsz_detail": hsz_detail,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# stammdaten
# ===================================================================


# ===================================================================
# uebergang (Bachelor -> Master)
# ===================================================================


_UEBERGANG_KATEGORIEN = [
    "kein_master",
    "am_jetzigen_ueberschneidung",
    "am_jetzigen_folgesemester",
    "am_jetzigen_pause",
    "an_anderem_ueberschneidung",
    "an_anderem_folgesemester",
    "an_anderem_pause",
]


def _classify_uebergang_detail(row: dict) -> str:
    """Klassifiziert eine Uebergangs-Zeile in detaillierte Kategorien."""
    m_pk = row.get("M_PK")
    if not m_pk:
        return "kein_master"

    b_hsz = (row.get("B_HSZ_K") or "").strip()
    m_hsz = (row.get("M_HSZ_K") or "").strip()
    b_ex = row.get("B_ExDatum")
    m_im = row.get("M_ImDatum")

    same_hsz = bool(b_hsz and m_hsz and b_hsz == m_hsz)
    prefix = "am_jetzigen" if same_hsz else "an_anderem"

    timing = "pause"
    if b_ex and m_im:
        try:
            diff_days = (m_im - b_ex).days
            if diff_days <= 0:
                timing = "ueberschneidung"
            elif diff_days <= 270:
                timing = "folgesemester"
        except Exception:
            pass

    return f"{prefix}_{timing}"


def _dedup_uebergang(rows: list[dict]) -> list[dict]:
    """Dedupliziert Uebergangs-Daten (eine Person pro Bachelor-Kohorte)."""
    seen: set = set()
    result = []
    for r in rows:
        key = (r.get("PersonenFID"), r.get("B_Kohorte"), r.get("M_PK"), r.get("M_HSZ_K"))
        if key in seen:
            continue
        seen.add(key)
        result.append(r)
    return result


def _best_row_per_person(kohorte_rows: list[dict]) -> dict:
    """Waehlt pro Person den besten Eintrag (frueheste Master-Einschreibung)."""
    persons: dict = {}
    for r in kohorte_rows:
        pid = r.get("PersonenFID")
        if pid not in persons:
            persons[pid] = r
            continue
        ex = persons[pid]
        ex_m = ex.get("M_PK")
        r_m = r.get("M_PK")
        if not ex_m and r_m:
            persons[pid] = r
        elif ex_m and r_m:
            ex_im = ex.get("M_ImDatum")
            r_im = r.get("M_ImDatum")
            if r_im and ex_im and r_im < ex_im:
                persons[pid] = r
    return persons


def _compute_uebergang_stats(rows: list[dict], kohorten_set: list[str]) -> tuple[dict, dict]:
    """Berechnet detaillierte Uebergangs-Statistiken pro Kohorte."""
    per_kohorte: dict = {}
    master_sg_per_kohorte: dict = {}

    for kohorte in kohorten_set:
        kohorte_rows = [r for r in rows if str(r.get("B_Kohorte")) == kohorte]
        persons = _best_row_per_person(kohorte_rows)

        total = len(persons) or 1
        counts = {k: 0 for k in _UEBERGANG_KATEGORIEN}
        sg_counts: dict = {}

        for r in persons.values():
            cat = _classify_uebergang_detail(r)
            if cat in counts:
                counts[cat] += 1
            m_sg = (r.get("M_SG") or "").strip()
            if m_sg:
                sg_counts[m_sg] = sg_counts.get(m_sg, 0) + 1

        per_kohorte[kohorte] = {"total": total, "counts": counts}
        master_sg_per_kohorte[kohorte] = sg_counts

    return per_kohorte, master_sg_per_kohorte


def _get_fom_uebergang_avg() -> dict | None:
    """Holt/cached den FOM-weiten Uebergangs-Durchschnitt."""
    cached = cache_get("_global_uebergang_fom")
    if cached:
        return cached

    fom_rows = query_db(queries.SQL_UEBERGANG_FOM)
    if not fom_rows:
        return None

    fom_rows = _dedup_uebergang(fom_rows)
    kohorten_set = sorted(
        set(str(r["B_Kohorte"]) for r in fom_rows if r.get("B_Kohorte")), reverse=True
    )
    per_kohorte, _ = _compute_uebergang_stats(fom_rows, kohorten_set)

    total_all = sum(d["total"] for d in per_kohorte.values()) or 1
    fom_avg = {}
    for kat in _UEBERGANG_KATEGORIEN:
        total_kat = sum(d["counts"][kat] for d in per_kohorte.values())
        fom_avg[f"{kat}_pct"] = round(total_kat / total_all * 100, 1)

    cache_set("_global_uebergang_fom", fom_avg)
    return fom_avg


def get_uebergang(produktkuerzel: str) -> dict:
    """Berechnet Uebergangsquote Bachelor -> Master.

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Uebergangs-Daten.
    """
    cache_key = f"uebergang_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_ueb, p_ueb = pk_expand_sql(queries.SQL_UEBERGANG, produktkuerzel)
    rows = query_db(sql_ueb, p_ueb)
    rows = _dedup_uebergang(rows)

    kohorten_set = sorted(
        set(str(r["B_Kohorte"]) for r in rows if r.get("B_Kohorte")), reverse=True
    )

    if not kohorten_set:
        return None

    per_kohorte, master_sg_per_kohorte = _compute_uebergang_stats(rows, kohorten_set)

    def pct_per_kohorte(kat: str) -> list[float]:
        return [
            round(per_kohorte[k]["counts"][kat] / per_kohorte[k]["total"] * 100, 1)
            for k in kohorten_set
        ]

    def sum_pct_per_kohorte(*kats: str) -> list[float]:
        return [
            round(
                sum(per_kohorte[k]["counts"][kat] for kat in kats) / per_kohorte[k]["total"] * 100,
                1,
            )
            for k in kohorten_set
        ]

    herkunft = {
        "kein_master": pct_per_kohorte("kein_master"),
        "am_jetzigen_hsz": sum_pct_per_kohorte(
            "am_jetzigen_ueberschneidung", "am_jetzigen_folgesemester", "am_jetzigen_pause"
        ),
        "am_jetzigen_ueberschneidung": pct_per_kohorte("am_jetzigen_ueberschneidung"),
        "am_jetzigen_folgesemester": pct_per_kohorte("am_jetzigen_folgesemester"),
        "am_jetzigen_pause": pct_per_kohorte("am_jetzigen_pause"),
        "an_anderem_hsz": sum_pct_per_kohorte(
            "an_anderem_ueberschneidung", "an_anderem_folgesemester", "an_anderem_pause"
        ),
        "an_anderem_ueberschneidung": pct_per_kohorte("an_anderem_ueberschneidung"),
        "an_anderem_folgesemester": pct_per_kohorte("an_anderem_folgesemester"),
        "an_anderem_pause": pct_per_kohorte("an_anderem_pause"),
    }

    # Top-8 Master-Studiengaenge mit Anteil pro Kohorte
    all_sg: dict = {}
    for sg_map in master_sg_per_kohorte.values():
        for sg, cnt in sg_map.items():
            all_sg[sg] = all_sg.get(sg, 0) + cnt
    top_sgs = sorted(all_sg.items(), key=lambda x: -x[1])[:8]
    master_studiengaenge = [
        {
            "name": sg,
            "werte": [
                round(
                    master_sg_per_kohorte.get(k, {}).get(sg, 0) / per_kohorte[k]["total"] * 100,
                    1,
                )
                for k in kohorten_set
            ],
        }
        for sg, _ in top_sgs
    ]

    # Uebersicht-Daten fuer Bar-Chart (Durchschnitt aller Kohorten)
    total_all = sum(d["total"] for d in per_kohorte.values()) or 1

    def avg_pct(kat: str) -> float:
        return round(sum(per_kohorte[k]["counts"][kat] for k in kohorten_set) / total_all * 100, 1)

    uebersicht_sg = [
        avg_pct("kein_master"),
        avg_pct("am_jetzigen_ueberschneidung"),
        avg_pct("am_jetzigen_folgesemester"),
        avg_pct("am_jetzigen_pause"),
        avg_pct("an_anderem_ueberschneidung"),
        avg_pct("an_anderem_folgesemester"),
        avg_pct("an_anderem_pause"),
    ]
    uebersicht_labels = [
        "kein Master",
        "m. Ueberschn.",
        "im Folgesem.",
        "nach Pause",
        "m. Ueberschn.",
        "im Folgesem.",
        "nach Pause",
    ]
    _GRP_AM_JETZIGEN = "am jetzigen HSZ"
    _GRP_AN_ANDEREM = "an anderem HSZ"
    uebersicht_gruppen = [
        None,
        _GRP_AM_JETZIGEN,
        _GRP_AM_JETZIGEN,
        _GRP_AM_JETZIGEN,
        _GRP_AN_ANDEREM,
        _GRP_AN_ANDEREM,
        _GRP_AN_ANDEREM,
    ]

    fom_avg = _get_fom_uebergang_avg()
    uebersicht_fom = (
        [
            fom_avg.get("kein_master_pct", 0),
            fom_avg.get("am_jetzigen_ueberschneidung_pct", 0),
            fom_avg.get("am_jetzigen_folgesemester_pct", 0),
            fom_avg.get("am_jetzigen_pause_pct", 0),
            fom_avg.get("an_anderem_ueberschneidung_pct", 0),
            fom_avg.get("an_anderem_folgesemester_pct", 0),
            fom_avg.get("an_anderem_pause_pct", 0),
        ]
        if fom_avg
        else None
    )

    data = {
        "kohorten": kohorten_set,
        "herkunft": herkunft,
        "master_studiengaenge": master_studiengaenge,
        "uebersicht_labels": uebersicht_labels,
        "uebersicht_gruppen": uebersicht_gruppen,
        "uebersicht_sg": uebersicht_sg,
        "uebersicht_fom": uebersicht_fom,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# herkunft (Studierendenherkunft nach Region)
# ===================================================================


def _classify_herkunft(row: dict) -> str:
    """Klassifiziert Herkunft: am_jetzigen_vorher/nachher, an_anderem_vorher/nachher."""
    same_hsz = row.get("GleicherHSZ") == 1
    b_ex = row.get("B_ExDatum")
    m_im = row.get("M_ImDatum")
    timing = "vorher" if (not b_ex or not m_im or str(b_ex) <= str(m_im)) else "nachher"
    prefix = "am_jetzigen" if same_hsz else "an_anderem"
    return f"{prefix}_{timing}"


def _classify_herkunft_detailed(row: dict) -> str:
    """Klassifiziert Herkunft feingranular fuer die Kohorten-Zeitreihe."""
    b_ex = row.get("B_ExDatum")
    m_im = row.get("M_ImDatum")
    if b_ex is None:
        return "nicht_intern"
    same_hsz = row.get("GleicherHSZ") == 1
    prefix = "am_jetzigen" if same_hsz else "an_anderem"
    b_str = str(b_ex)[:10]
    m_str = str(m_im)[:10] if m_im else b_str
    if b_str > m_str:
        return f"{prefix}_ueberschneidung"
    try:
        gap = (date.fromisoformat(m_str) - date.fromisoformat(b_str)).days
        sub = "folgesemester" if gap <= 180 else "pause"
    except Exception:
        sub = "folgesemester"
    return f"{prefix}_{sub}"


def _top10_pct(d: dict, total: int) -> list:
    top = sorted(d.items(), key=lambda x: -x[1])[:10]
    return [{"name": k, "pct": round(v / total * 100, 1)} for k, v in top]


def _compute_herkunft_stats(data_rows: list) -> dict:
    """Berechnet Herkunfts-Statistiken (Top-SG, Studienrichtungen, Uebersicht)."""
    total = len(data_rows) or 1
    sg_counts: dict = {}
    sg_gleich: dict = {}
    sg_anders: dict = {}
    studienrichtungen: dict = {}
    studienrichtungen_gleich: dict = {}
    studienrichtungen_anders: dict = {}
    uebersicht: dict = {}

    for r in data_rows:
        b_sg = r.get("B_SG") or "Unbekannt"
        b_familie = r.get("B_Familie") or ""
        same_hsz = r.get("GleicherHSZ") == 1
        sg_counts[b_sg] = sg_counts.get(b_sg, 0) + 1
        if same_hsz:
            sg_gleich[b_sg] = sg_gleich.get(b_sg, 0) + 1
        else:
            sg_anders[b_sg] = sg_anders.get(b_sg, 0) + 1
        studienrichtungen[b_familie] = studienrichtungen.get(b_familie, 0) + 1
        if same_hsz:
            studienrichtungen_gleich[b_familie] = studienrichtungen_gleich.get(b_familie, 0) + 1
        else:
            studienrichtungen_anders[b_familie] = studienrichtungen_anders.get(b_familie, 0) + 1
        cat = _classify_herkunft(r)
        uebersicht[cat] = uebersicht.get(cat, 0) + 1

    uebersicht_keys = [
        "am_jetzigen_vorher", "am_jetzigen_nachher",
        "an_anderem_vorher", "an_anderem_nachher",
    ]
    return {
        "bachelor_studiengaenge": _top10_pct(sg_counts, total),
        "bachelor_studiengaenge_gleich": _top10_pct(sg_gleich, total),
        "bachelor_studiengaenge_anders": _top10_pct(sg_anders, total),
        "top_studienrichtungen": _top10_pct(studienrichtungen, total),
        "top_studienrichtungen_gleich": _top10_pct(studienrichtungen_gleich, total),
        "top_studienrichtungen_anders": _top10_pct(studienrichtungen_anders, total),
        "uebersicht_labels": [
            "am jetzigen HSZ\n(vorher)", "am jetzigen HSZ\n(nachher)",
            "an anderem HSZ\n(vorher)", "an anderem HSZ\n(nachher)",
        ],
        "uebersicht_vals": [round(uebersicht.get(k, 0) / total * 100, 1) for k in uebersicht_keys],
    }


_HERKUNFT_SERIES_KEYS = [
    "nicht_intern", "am_jetzigen_hsz",
    "am_jetzigen_ueberschneidung", "am_jetzigen_folgesemester", "am_jetzigen_pause",
    "an_anderem_hsz", "an_anderem_ueberschneidung", "an_anderem_folgesemester", "an_anderem_pause",
]
_HERKUNFT_PARENT_MAP = {
    "am_jetzigen_ueberschneidung": "am_jetzigen_hsz",
    "am_jetzigen_folgesemester": "am_jetzigen_hsz",
    "am_jetzigen_pause": "am_jetzigen_hsz",
    "an_anderem_ueberschneidung": "an_anderem_hsz",
    "an_anderem_folgesemester": "an_anderem_hsz",
    "an_anderem_pause": "an_anderem_hsz",
}


def _build_kohorten_series(kohorten: list, kohorte_rows_map: dict) -> dict:
    """Baut Herkunfts-Zeitreihe je Kohorte."""
    series: dict = {key: [] for key in _HERKUNFT_SERIES_KEYS}
    for k in kohorten:
        k_rows = kohorte_rows_map[k]
        total_k = len(k_rows) or 1
        counts: dict = {key: 0 for key in _HERKUNFT_SERIES_KEYS}
        for r in k_rows:
            cat = _classify_herkunft_detailed(r)
            if cat in counts:
                counts[cat] += 1
                parent = _HERKUNFT_PARENT_MAP.get(cat)
                if parent:
                    counts[parent] += 1
        for key in _HERKUNFT_SERIES_KEYS:
            series[key].append(round(counts[key] / total_k * 100, 1))
    return series


def _add_kohorten_werte_pct(
    items: list, field: str, kohorten: list, kohorte_rows_map: dict, filter_val: int | None = None
) -> list:
    """Erweitert items um Prozentwerte je Kohorte."""
    result = []
    for item in items:
        name = item["name"]
        werte = []
        for k in kohorten:
            k_rows = kohorte_rows_map[k]
            if filter_val is not None:
                k_rows = [r for r in k_rows if r.get("GleicherHSZ") == filter_val]
            total_k = len(k_rows) or 1
            cnt = sum(1 for r in k_rows if (r.get(field) or "Unbekannt") == name)
            werte.append(round(cnt / total_k * 100, 1))
        result.append({**item, "werte": werte})
    return result


def _add_kohorten_werte_cnt(
    items: list, field: str, kohorten: list, kohorte_rows_map: dict, filter_val: int | None = None
) -> list:
    """Erweitert items um Anzahl-Werte je Kohorte."""
    result = []
    for item in items:
        name = item["name"]
        werte = []
        for k in kohorten:
            k_rows = kohorte_rows_map[k]
            if filter_val is not None:
                k_rows = [r for r in k_rows if r.get("GleicherHSZ") == filter_val]
            cnt = sum(1 for r in k_rows if (r.get(field) or "") == name)
            werte.append(cnt)
        result.append({**item, "werte": werte})
    return result


def get_herkunft(produktkuerzel: str) -> dict:
    """Berechnet die regionale Herkunft der Studierenden.

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Herkunfts-Daten (Bundeslaender, HSZ-Wechsel etc.).
    """
    cache_key = f"herkunft_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_hk, p_hk = pk_expand_sql(queries.SQL_HERKUNFT, produktkuerzel)
    rows = query_db(sql_hk, p_hk)

    fom_rows = cache_get("_global_herkunft_fom")
    if not fom_rows:
        fom_rows = query_db(queries.SQL_HERKUNFT_FOM)
        cache_set("_global_herkunft_fom", fom_rows)

    sg_stats = _compute_herkunft_stats(rows)
    fom_stats = _compute_herkunft_stats(fom_rows)

    kohorten = sorted(set(r.get("M_Kohorte") for r in rows if r.get("M_Kohorte")))[-5:]
    kohorte_rows_map = {k: [r for r in rows if r.get("M_Kohorte") == k] for k in kohorten}
    herkunft_series = _build_kohorten_series(kohorten, kohorte_rows_map)

    hsz_set = sorted(set(r.get("M_HSZ") for r in rows if r.get("M_HSZ")))
    hsz_detail = {hsz: _compute_herkunft_stats([r for r in rows if r.get("M_HSZ") == hsz])
                  for hsz in hsz_set}

    data = {
        **sg_stats,
        "uebersicht_gruppen": sg_stats["uebersicht_labels"],
        "uebersicht_fom": fom_stats["uebersicht_vals"],
        "uebersicht_sg": sg_stats["uebersicht_vals"],
        "hsz_detail": hsz_detail,
        "kohorten": kohorten,
        "herkunft": herkunft_series,
        "bachelor_studiengaenge": _add_kohorten_werte_pct(
            sg_stats["bachelor_studiengaenge"], "B_SG", kohorten, kohorte_rows_map
        ),
        "bachelor_studiengaenge_gleich": _add_kohorten_werte_pct(
            sg_stats["bachelor_studiengaenge_gleich"], "B_SG", kohorten, kohorte_rows_map,
            filter_val=1
        ),
        "bachelor_studiengaenge_anders": _add_kohorten_werte_pct(
            sg_stats["bachelor_studiengaenge_anders"], "B_SG", kohorten, kohorte_rows_map,
            filter_val=0
        ),
        "top_studienrichtungen": _add_kohorten_werte_cnt(
            sg_stats["top_studienrichtungen"], "B_Familie", kohorten, kohorte_rows_map
        ),
        "top_studienrichtungen_gleich": _add_kohorten_werte_cnt(
            sg_stats["top_studienrichtungen_gleich"], "B_Familie", kohorten, kohorte_rows_map,
            filter_val=1
        ),
        "top_studienrichtungen_anders": _add_kohorten_werte_cnt(
            sg_stats["top_studienrichtungen_anders"], "B_Familie", kohorten, kohorte_rows_map,
            filter_val=0
        ),
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# zuzahler
# ===================================================================


def get_zuzahler(produktkuerzel: str) -> dict:
    """Berechnet Zuzahler-Anteil und Top-10-Berufe.

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Zuzahler-Zeitreihe und Vergleichsdaten.
    """
    cache_key = f"zuzahler_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_zuz, p_zuz = pk_expand_sql(queries.SQL_ZUZAHLER, produktkuerzel)
    zuz_rows = query_db(sql_zuz, p_zuz)

    # FOM-weit cachen
    zuz_fom = cache_get("_global_zuzahler_fom")
    if not zuz_fom:
        zuz_fom = query_db(queries.SQL_ZUZAHLER_FOM)
        cache_set("_global_zuzahler_fom", zuz_fom)

    # Auf 7 Semester begrenzen
    zuz_rows = _semester_filter_7(zuz_rows)
    zuz_fom_filtered = _semester_filter_7(zuz_fom)

    semester = sorted(set(r["Semesterkuerzel"] for r in zuz_rows))
    semester_labels = [_fmt_sem(s) for s in semester]

    # SG-Daten
    sg_gesamt = []
    sg_zuzahler = []
    sg_pct = []
    for sem in semester:
        sem_rows = [r for r in zuz_rows if r["Semesterkuerzel"] == sem]
        gesamt = sum(int(r.get("Total", 0) or 0) for r in sem_rows)
        zuz = sum(int(r.get("Zuzahler", 0) or 0) for r in sem_rows)
        sg_gesamt.append(gesamt)
        sg_zuzahler.append(zuz)
        sg_pct.append(round(zuz / max(gesamt, 1) * 100, 1))

    # FOM-Daten
    fom_pct = []
    for sem in semester:
        fom_sem = [r for r in zuz_fom_filtered if r["Semesterkuerzel"] == sem]
        gesamt = sum(int(r.get("Total", 0) or 0) for r in fom_sem)
        zuz = sum(int(r.get("Zuzahler", 0) or 0) for r in fom_sem)
        fom_pct.append(round(zuz / max(gesamt, 1) * 100, 1))

    data = {
        "semester": semester_labels,
        "absolut": sg_zuzahler,
        "pct_sg": sg_pct,
        "pct_fom": fom_pct,
        "top10": [],
        "gesamtergebnis": sg_zuzahler,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# vertiefungsrichtungen
# ===================================================================


def _build_vr_table(filtered_rows: list, semesters: list) -> tuple[list, list]:
    """Baut Pivot-Tabelle fuer Vertiefungsrichtungen oder Wahlpflichtmodule."""
    names = sorted(
        set(r.get("Vertiefungsname") or r.get("Modulname") or "?" for r in filtered_rows)
    )
    items = []
    gesamt_per_sem = [0] * len(semesters)
    for name in names:
        vals = []
        for i, sem in enumerate(semesters):
            cnt = sum(
                int(r.get("Anzahl", 0) or 0)
                for r in filtered_rows
                if (r.get("Vertiefungsname") or r.get("Modulname") or "?") == name
                and r["Semesterkuerzel"] == sem
            )
            vals.append(cnt)
            gesamt_per_sem[i] += cnt
        items.append({"name": name, "werte": vals})
    return items, gesamt_per_sem


def _load_hochschulzertifikate(produktkuerzel: str) -> dict:
    """Laedt Hochschulzertifikat-Daten und gibt Pivot-Dict zurueck (leer bei Fehler)."""
    try:
        sql_hz, p_hz = pk_expand_sql(queries.SQL_HOCHSCHULZERTIFIKATE, produktkuerzel, count=1)
        hz_rows = query_db(sql_hz, p_hz)
        if not hz_rows:
            return {}
        hz_blocks = sorted(set(r["Block"] for r in hz_rows if r["Block"]))
        hz_names = sorted(set(r["Zertifikat"] for r in hz_rows))
        hz_items = []
        for name in hz_names:
            vals = [
                sum(
                    int(r.get("Anzahl", 0) or 0)
                    for r in hz_rows
                    if r["Zertifikat"] == name and r["Block"] == block
                )
                for block in hz_blocks
            ]
            hz_items.append({"name": name, "werte": vals})
        return {"hz_blocks": hz_blocks, "hz_zertifikate": hz_items}
    except Exception:
        return {}


def get_vertiefungsrichtungen(produktkuerzel: str) -> dict | None:
    """Berechnet Vertiefungsrichtungen und Wahlpflichtmodule.

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit VR/WP-Daten oder None wenn keine Daten vorhanden.
    """
    cache_key = f"vertiefungsrichtungen_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_vr, p_vr = pk_expand_sql(queries.SQL_VERTIEFUNGSRICHTUNGEN, produktkuerzel)
    rows = query_db(sql_vr, p_vr)

    if not rows:
        return None

    cur_sem = _aktuelles_semester()
    all_semesters = sorted(set(r["Semesterkuerzel"] for r in rows if r["Semesterkuerzel"]))
    all_semesters = [s for s in all_semesters if s <= cur_sem][-7:]
    rows = [r for r in rows if r["Semesterkuerzel"] in set(all_semesters)]

    semester_labels = [_fmt_sem(s) for s in all_semesters]
    vr_rows = [r for r in rows if r.get("Wahlart") == "Vertiefungsrichtung"]
    wp_rows = [r for r in rows if r.get("Wahlart") != "Vertiefungsrichtung"]

    data: dict = {"semester": semester_labels}

    if vr_rows:
        vr_items, vr_gesamt = _build_vr_table(vr_rows, all_semesters)
        data["vr_semester"] = semester_labels
        data["vr_module"] = vr_items
        data["vr_gesamt"] = vr_gesamt

    if wp_rows:
        wp_items, wp_gesamt = _build_vr_table(wp_rows, all_semesters)
        data["wp_semester"] = semester_labels
        data["wp_module"] = wp_items
        data["wp_gesamt"] = wp_gesamt

    data.update(_load_hochschulzertifikate(produktkuerzel))

    cache_set(cache_key, data)
    return data


# ===================================================================
# rahmendaten
# ===================================================================


def _lookup_fachsemester(modules_without_sem: set, variants: list) -> tuple[dict, dict]:
    """Sucht fehlende Fachsemester per VP-Aliases und Grow-Fallback."""
    vp_aliases_mapping: dict = {}
    if modules_without_sem:
        ph_mods = ",".join("?" * len(modules_without_sem))
        ph_pks = ",".join("?" * len(variants))
        sql_vp = queries.SQL_VP_ALIASES_SEMESTER.replace("{pk_placeholders}", ph_pks).replace(
            "{mod_placeholders}", ph_mods
        )
        vp_rows = query_db(sql_vp, variants + list(modules_without_sem))
        for r in vp_rows:
            vp_aliases_mapping[int(r["ModulFID"])] = int(r["Fachsemester"])

    grow_mapping: dict = {}
    still_missing = modules_without_sem - set(vp_aliases_mapping.keys())
    if still_missing:
        ph_grow = ",".join("?" * len(still_missing))
        sql_grow = queries.SQL_GROW_SEMESTER.replace("{placeholders}", ph_grow)
        grow_rows = query_db(sql_grow, list(still_missing))
        for r in grow_rows:
            grow_mapping[int(r["ModulID"])] = int(r["Fachsemester"])

    return vp_aliases_mapping, grow_mapping


def _aggregate_ue(
    ue_rows: list, vp_aliases_mapping: dict, grow_mapping: dict
) -> tuple[dict, dict]:
    """Aggregiert UE-Stunden nach Typ und Fachsemester."""
    ue: dict = {}
    ue_by_semester: dict = {}
    for r in ue_rows:
        typ = r["UETyp"]
        val = int(r["TotalUE"] or 0)
        if typ not in ("praxis", "virtuell", "folgt"):
            continue
        modul_id = int(r["ModulFID"]) if r["ModulFID"] else None
        sem_vp = int(r["Fachsemester"]) if r["Fachsemester"] is not None else None
        sem_aliases = vp_aliases_mapping.get(modul_id) if modul_id else None
        sem_grow = grow_mapping.get(modul_id) if modul_id else None
        sem = sem_vp if sem_vp is not None else (sem_aliases if sem_aliases is not None else sem_grow)
        sem_key = int(sem) if sem is not None else 0

        ue[typ] = ue.get(typ, 0) + val
        ue_by_semester.setdefault(sem_key, {})
        ue_by_semester[sem_key][typ] = ue_by_semester[sem_key].get(typ, 0) + val
    return ue, ue_by_semester


def _load_ue_verteilung(produktkuerzel: str) -> tuple[dict, dict]:
    """Laedt und aggregiert UE-Verteilung inkl. Fachsemester-Fallbacks."""
    import traceback

    try:
        variants = expand_pk(produktkuerzel)
        ph_buchungen = ",".join("?" * len(variants))
        sql_parts = queries.SQL_UES.split("= ?")
        sql_ues_final = sql_parts[0] + "= ?" + sql_parts[1] + f"IN ({ph_buchungen})" + sql_parts[2]
        p_ues = [produktkuerzel] + variants
        ue_rows = query_db(sql_ues_final, p_ues)

        modules_without_sem: set = set()
        for r in ue_rows:
            mod_id = int(r["ModulFID"]) if r["ModulFID"] else None
            if mod_id and r["Fachsemester"] is None:
                modules_without_sem.add(mod_id)

        vp_aliases_mapping, grow_mapping = _lookup_fachsemester(modules_without_sem, variants)
        return _aggregate_ue(ue_rows, vp_aliases_mapping, grow_mapping)
    except Exception as exc:
        print(f"[UE-Fehler] {produktkuerzel}: {exc}")
        traceback.print_exc()
        return {}, {}


def get_rahmendaten(produktkuerzel: str) -> dict:
    """Berechnet Rahmendaten (Zeitmodelle, UE-Verteilung).

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Rahmendaten.
    """
    cache_key = f"rahmendaten_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    sql_rahmen, p_rahmen = pk_expand_sql(queries.SQL_RAHMENDATEN, produktkuerzel)
    rahmen_rows = query_db(sql_rahmen, p_rahmen)

    sql_sf, p_sf = pk_expand_sql(queries.SQL_STUDIENFORMATE, produktkuerzel)
    sf_rows = query_db(sql_sf, p_sf)
    studienformate = [r["Studienformat"] for r in sf_rows if r.get("Studienformat")]

    zeitmodelle = [r["Zeitmodell"] for r in rahmen_rows if r.get("Zeitmodell")]
    im_angebot_seit = None
    if rahmen_rows:
        erste = min(
            (r["ErstesAngebot"] for r in rahmen_rows if r.get("ErstesAngebot")),
            default=None,
        )
        if erste:
            im_angebot_seit = str(erste)[:10]

    ue, ue_by_semester = _load_ue_verteilung(produktkuerzel)

    data = {
        "imAngebotSeit": im_angebot_seit,
        "zeitmodelle": zeitmodelle,
        "studienformate": studienformate,
        "akkreditierungsDatum": "",
        "verantwortlicherDekan": "",
        "ue": ue,
        "ueBySemester": ue_by_semester,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# anrechnungen
# ===================================================================


def get_anrechnungen(produktkuerzel: str) -> dict:
    """Berechnet Anrechnungs-Statistiken (HS, Beruflich, Offene Hochschule).

    Nutzt primaer die neuen Anrechnung_*-Tabellen (ab Mai 2026) und faellt
    fuer aeltere Eintraege auf se.AnrechnungsGrund zurueck.

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Anrechnungs-Daten.
    """
    cache_key = f"anrechnungen_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    variants = expand_pk(produktkuerzel)
    pk_placeholders = ",".join("?" * len(variants))

    # Haupt-Query: Population + Klassifizierung (3-stufige Logik)
    # Quelle 1: Anrechnung_Grundlage.GrundlagenTyp (neue Logik ab Mai)
    # Quelle 2: AntragLeistungsart + Leistungsart (aeltere Eintraege ohne Grundlage)
    # Fallback:  pe.AnerkanntText LIKE-Suche (fuer Eintraege ohne Antrags-Daten)
    sql = f"""
        WITH gs_anr AS (
            SELECT DISTINCT
                se.StudienEintragID,
                se.PersonenFID
            FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
                INNER JOIN BCW_DWH.dwh.StudienEintraege se
                    ON se.StudienEintragID = sz.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l
                    ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_DWH.dwh.StatusGruppen sg
                    ON sg.Status = sz.Status
            WHERE sg.StatusGruppe IN (
                    '{config_db.get_param("anrechnungen", "statusgruppe_1", "Beginner mit UV")}',
                    '{config_db.get_param("anrechnungen", "statusgruppe_2", "Quereinsteiger mit UV")}')
              AND sz.Semesterkuerzel >= CONCAT(
                  YEAR(GETDATE()) - {config_db.get_param_int("anrechnungen", "semester_zurueck", 6)},
                  CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS'
                       WHEN MONTH(GETDATE()) >= 3 THEN '-SS'
                       ELSE '-WS' END)
              AND sz.Semesterkuerzel <= CASE
                  WHEN MONTH(GETDATE()) >= 9 THEN CONCAT(YEAR(GETDATE()), '-WS')
                  WHEN MONTH(GETDATE()) >= 3 THEN CONCAT(YEAR(GETDATE()), '-SS')
                  ELSE CONCAT(YEAR(GETDATE())-1, '-WS')
              END
              AND se.ImmatrikulationsDatum IS NOT NULL
              AND l.Hochschulzentrum NOT IN ({config_db.EXCLUDED_HSZ_SQL})
              AND l.Ausrichtung = 'national'
              AND l.Produktkuerzel IN ({pk_placeholders})
        ),
        neu_anr_grundlage AS (
            -- Quelle 1: Anrechnung_Grundlage.GrundlagenTyp (neue Logik ab Mai)
            SELECT
                atn.StnId AS StudienEintragID,
                MAX(CASE WHEN gl.GrundlagenTyp = 'Hochschulische Leistung'
                         THEN 1 ELSE 0 END) AS hat_hs,
                MAX(CASE WHEN gl.GrundlagenTyp IN ('Ausbildung', 'Weiterbildung')
                         THEN 1 ELSE 0 END) AS hat_ber
            FROM BCW_STA.mariadb.Anrechnung_AntragTN atn
                INNER JOIN BCW_STA.mariadb.Anrechnung_Ergebnis e
                    ON e.AnrechnungAntragTNFid = atn.Id
                INNER JOIN BCW_STA.mariadb.Anrechnung_ErgebnisModule em
                    ON em.AnrechnungErgebnisFid = e.Id
                INNER JOIN BCW_STA.mariadb.Anrechnung_Grundlage gl
                    ON gl.AnrechnungantragTNFid = atn.Id
            WHERE em.Anrechenbarkeit = 'angerechnet'
            GROUP BY atn.StnId
        ),
        neu_anr_leistungsart AS (
            -- Quelle 2: AntragLeistungsart + Leistungsart (aeltere Eintraege ohne Grundlage)
            SELECT
                gs.StudienEintragID,
                MAX(CASE WHEN la.LeistungsArtAnzeigeName LIKE '%Hochschulische Leistung%'
                         THEN 1 ELSE 0 END) AS hat_hs,
                MAX(
                    CASE
                        WHEN la.LeistungsArtAnzeigeName LIKE '%Ausbildung%'
                             OR la.LeistungsArtAnzeigeName LIKE '%Ausserhochschulische Leistung%'
                        THEN 1 ELSE 0
                    END
                ) AS hat_ber
            FROM gs_anr gs
                INNER JOIN BCW_STA.mariadb.Antraege a
                    ON a.PersonenFID = gs.PersonenFID
                INNER JOIN BCW_STA.mariadb.AntragLeistungsart al
                    ON al.AntragFiD = a.Id
                INNER JOIN BCW_STA.mariadb.Leistungsart la
                    ON al.LeistungsartFId = la.Id
                INNER JOIN BCW_STA.mariadb.Ergebnisse erg
                    ON erg.AnrechnungenFid = a.Id
                LEFT JOIN BCW_DWH.dwh.Lehrgaenge l2
                    ON erg.VerwaltungsPruefungsordnungFid = l2.POID
            WHERE la.LeistungsArtAnzeigeName NOT IN (
                      'Einschreibehindernispruefung', 'Kooperation')
              AND l2.Produktkuerzel IN ({pk_placeholders})
              AND gs.StudienEintragID NOT IN (
                  SELECT StudienEintragID FROM neu_anr_grundlage)
            GROUP BY gs.StudienEintragID
        ),
        neu_anr AS (
            -- Zusammenfuehren beider Quellen (Kombi-Kategorie moeglich)
            SELECT
                StudienEintragID,
                CASE
                    WHEN hat_hs = 1 AND hat_ber = 1 THEN 'HsBer'
                    WHEN hat_hs = 1 THEN 'Hochschulisch'
                    ELSE 'Beruflich'
                END AS Kategorie
            FROM neu_anr_grundlage
            UNION ALL
            SELECT
                StudienEintragID,
                CASE
                    WHEN hat_hs = 1 AND hat_ber = 1 THEN 'HsBer'
                    WHEN hat_hs = 1 THEN 'Hochschulisch'
                    ELSE 'Beruflich'
                END AS Kategorie
            FROM neu_anr_leistungsart
        ),
        anr_text AS (
            -- Fallback: AnerkanntText aus Noten (fuer Eintraege ohne Antrags-Daten)
            SELECT
                n.StudienEintragFID AS StudienEintragID,
                MAX(
                    CASE
                        WHEN pe.AnerkanntText LIKE '%HS%'
                             OR pe.AnerkanntText LIKE '%Auslandsstudium%'
                             OR pe.AnerkanntText LIKE '%ERASMUS%'
                        THEN 1 ELSE 0
                    END
                ) AS hat_hs,
                MAX(
                    CASE
                        WHEN pe.AnerkanntText NOT LIKE '%HS%'
                             AND pe.AnerkanntText NOT LIKE '%Auslandsstudium%'
                             AND pe.AnerkanntText NOT LIKE '%ERASMUS%'
                        THEN 1 ELSE 0
                    END
                ) AS hat_ber
            FROM BCW_DWH.dwh.Noten n
                INNER JOIN BCW_STA.mariadb.t_pruefungsergebnisse pe
                    ON pe.PruefungsErgebnisID = n.PruefungsErgebnisFID
                INNER JOIN gs_anr gs
                    ON gs.StudienEintragID = n.StudienEintragFID
            WHERE pe.Anerkannt NOT IN ('N', 'Z')
              AND pe.AnerkanntText IS NOT NULL
              AND LTRIM(RTRIM(pe.AnerkanntText)) <> ''
            GROUP BY n.StudienEintragFID
        ),
        klassifiziert AS (
            SELECT
                gs.StudienEintragID,
                CASE
                    WHEN na.StudienEintragID IS NOT NULL THEN na.Kategorie
                    WHEN anrt.StudienEintragID IS NOT NULL THEN
                        CASE
                            WHEN anrt.hat_hs = 1 AND anrt.hat_ber = 1 THEN 'HsBer'
                            WHEN anrt.hat_hs = 1 THEN 'Hochschulisch'
                            WHEN anrt.hat_ber = 1 THEN 'Beruflich'
                            ELSE 'Keine'
                        END
                    ELSE 'Keine'
                END AS Kategorie
            FROM gs_anr gs
                LEFT JOIN neu_anr na ON na.StudienEintragID = gs.StudienEintragID
                LEFT JOIN anr_text anrt ON anrt.StudienEintragID = gs.StudienEintragID
        )
        SELECT
            COUNT(DISTINCT StudienEintragID) AS Total,
            COUNT(DISTINCT CASE WHEN Kategorie <> 'Keine'
                                THEN StudienEintragID END) AS MitAnrechnung,
            COUNT(DISTINCT CASE WHEN Kategorie = 'Beruflich'
                                THEN StudienEintragID END) AS Beruflich,
            COUNT(DISTINCT CASE WHEN Kategorie = 'Hochschulisch'
                                THEN StudienEintragID END) AS Hochschulisch,
            COUNT(DISTINCT CASE WHEN Kategorie = 'HsBer'
                                THEN StudienEintragID END) AS HsBer,
            COUNT(DISTINCT CASE WHEN Kategorie = 'Keine'
                                THEN StudienEintragID END) AS Keine
        FROM klassifiziert
    """

    rows = query_db(sql, variants + variants)
    s = rows[0] if rows else {}
    total = max(int(s.get("Total", 0) or 0), 1)
    mit_anrechnung = int(s.get("MitAnrechnung", 0) or 0)
    anteil_pct = round(mit_anrechnung / total * 100, 1)
    beruflich_abs = int(s.get("Beruflich", 0) or 0)
    hochschulisch_abs = int(s.get("Hochschulisch", 0) or 0)
    hs_ber_abs = int(s.get("HsBer", 0) or 0)
    keine_abs = int(s.get("Keine", 0) or 0)
    hochschulisch_pct = round(hochschulisch_abs / total * 100, 1)
    beruflich_pct = round(beruflich_abs / total * 100, 1)
    hs_ber_pct = round(hs_ber_abs / total * 100, 1)
    keine_pct = round(keine_abs / total * 100, 1)
    offene_hs_pct = beruflich_pct  # Offene Hochschule = berufliche Qualifikation

    # Top-10 angerechnete Module: alte Quelle (pe.Anerkannt) + neue Quelle (ErgebnisModule)
    # Eingeschraenkt auf Population (Beginner/Quereinsteiger mit UV, letzte Semester)
    sql_top = f"""
        WITH gs_pop AS (
            SELECT DISTINCT se.StudienEintragID
            FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
                INNER JOIN BCW_DWH.dwh.StudienEintraege se
                    ON se.StudienEintragID = sz.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l
                    ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_DWH.dwh.StatusGruppen sg
                    ON sg.Status = sz.Status
            WHERE sg.StatusGruppe IN (
                    '{config_db.get_param("anrechnungen", "statusgruppe_1", "Beginner mit UV")}',
                    '{config_db.get_param("anrechnungen", "statusgruppe_2", "Quereinsteiger mit UV")}')
              AND sz.Semesterkuerzel >= CONCAT(
                  YEAR(GETDATE()) - {config_db.get_param_int("anrechnungen", "semester_zurueck", 6)},
                  CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS'
                       WHEN MONTH(GETDATE()) >= 3 THEN '-SS'
                       ELSE '-WS' END)
              AND sz.Semesterkuerzel <= CASE
                  WHEN MONTH(GETDATE()) >= 9 THEN CONCAT(YEAR(GETDATE()), '-WS')
                  WHEN MONTH(GETDATE()) >= 3 THEN CONCAT(YEAR(GETDATE()), '-SS')
                  ELSE CONCAT(YEAR(GETDATE())-1, '-WS')
              END
              AND se.ImmatrikulationsDatum IS NOT NULL
              AND l.Hochschulzentrum NOT IN ({config_db.EXCLUDED_HSZ_SQL})
              AND l.Ausrichtung = 'national'
              AND l.Produktkuerzel IN ({pk_placeholders})
        )
        SELECT TOP 10 Name, SUM(Cnt) AS Cnt FROM (
            SELECT
                mb.Bezeichnung AS Name,
                COUNT(DISTINCT n.StudienEintragFID) AS Cnt
            FROM BCW_DWH.dwh.Noten n
                INNER JOIN gs_pop gs ON gs.StudienEintragID = n.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.StudienEintraege se
                    ON se.StudienEintragID = n.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l
                    ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_STA.mariadb.t_pruefungsergebnisse pe
                    ON pe.PruefungsErgebnisID = n.PruefungsErgebnisFID
                INNER JOIN BCW_STA.mariadb.t_modulbeschreibung mb
                    ON mb.ModulID = n.ModulFID
            WHERE l.Produktkuerzel IN ({pk_placeholders})
              AND l.Institut = 'FOM'
              AND l.Ausrichtung = 'national'
              AND l.Hochschulzentrum NOT IN ({config_db.EXCLUDED_HSZ_SQL})
              AND pe.Anerkannt = 'Y'
              AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
            GROUP BY mb.Bezeichnung

            UNION ALL

            SELECT
                em.ModulName AS Name,
                COUNT(DISTINCT atn.StnId) AS Cnt
            FROM BCW_STA.mariadb.Anrechnung_AntragTN atn
                INNER JOIN gs_pop gs ON gs.StudienEintragID = atn.StnId
                INNER JOIN BCW_DWH.dwh.StudienEintraege se
                    ON se.StudienEintragID = atn.StnId
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l
                    ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_STA.mariadb.Anrechnung_Ergebnis e
                    ON e.AnrechnungAntragTNFid = atn.Id
                INNER JOIN BCW_STA.mariadb.Anrechnung_ErgebnisModule em
                    ON em.AnrechnungErgebnisFid = e.Id
            WHERE l.Produktkuerzel IN ({pk_placeholders})
              AND l.Institut = 'FOM'
              AND l.Ausrichtung = 'national'
              AND l.Hochschulzentrum NOT IN ({config_db.EXCLUDED_HSZ_SQL})
              AND em.Anrechenbarkeit = 'angerechnet'
              AND atn.StnId NOT IN (
                  SELECT DISTINCT n2.StudienEintragFID
                  FROM BCW_DWH.dwh.Noten n2
                  INNER JOIN BCW_STA.mariadb.t_pruefungsergebnisse pe2
                      ON pe2.PruefungsErgebnisID = n2.PruefungsErgebnisFID
                  WHERE pe2.Anerkannt = 'Y'
                    AND n2.StudienEintragFID = atn.StnId
              )
            GROUP BY em.ModulName
        ) combined
        GROUP BY Name
        ORDER BY SUM(Cnt) DESC
    """
    top_module_rows = query_db(sql_top, variants + variants + variants)

    data = {
        "total_population": total,
        "mit_anrechnung": mit_anrechnung,
        "anteil_pct": anteil_pct,
        "hochschulisch_abs": hochschulisch_abs,
        "beruflich_abs": beruflich_abs,
        "hs_ber_abs": hs_ber_abs,
        "keine_abs": keine_abs,
        "hochschulisch_pct": hochschulisch_pct,
        "beruflich_pct": beruflich_pct,
        "hs_ber_pct": hs_ber_pct,
        "keine_pct": keine_pct,
        "offene_hochschule_pct": offene_hs_pct,
        "top_module": [{"name": r["Name"], "anzahl": int(r["Cnt"])} for r in top_module_rows],
    }
    cache_set(cache_key, data)
    return data
