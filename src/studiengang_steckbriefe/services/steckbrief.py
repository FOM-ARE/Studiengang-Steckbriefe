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

    PK_MAPPING = config_db.PK_MAPPING
    NAME_MAPPING = {
        "Business Administration - Healthcare Management": "Business Administration",
        "Business Administration - dual kompakt": "Business Administration",
        "Business Administration Vertiefung Public Management": "Business Administration",
        "Business Administration, Vertiefung Public Management": "Business Administration",
        "Business Administration - Public Management": "Business Administration",
        "Business Administration \u2013 Versicherungsbetrieb": "Business Administration",
        "Business Administration \u2013 Versicherungsvertrieb": "Business Administration",
        "Engineering & Management": "Wirtschaftsingenieurwesen",
        "Prim\u00e4rmedizinisches Versorgungs- und Praxismanagement": "Primary Care Management",
        "Soziale Arbeit - kommunal": "Soziale Arbeit",
        "Soziale Arbeit \u2013 kommunal": "Soziale Arbeit",
        "Wirtschaftsinformatik \u2013 kommunal": "Wirtschaftsinformatik",
        "Wirtschaftsinformatik - kommunal": "Wirtschaftsinformatik",
    }

    # Studierende-Map auf zusammengefasste PKs umrechnen
    merged_stud: dict[str, int] = {}
    for pk, count in stud_map.items():
        merged_pk = PK_MAPPING.get(pk, pk)
        merged_stud[merged_pk] = merged_stud.get(merged_pk, 0) + count

    # Deduplizieren + Zusammenfassen
    sg_map: dict[str, dict] = {}
    for r in rows:
        raw_pk = r["Produktkuerzel"]
        pk = PK_MAPPING.get(raw_pk, raw_pk)
        sg_name = r["Studiengang"] or ""
        name_match = re.match(r"^(.+?)\s*\([^)]+\)\s*$", sg_name)
        base_name = name_match.group(1).strip() if name_match else sg_name
        base_name = NAME_MAPPING.get(base_name, base_name)
        display_name = f"{base_name} ({pk})"

        if pk not in sg_map or len(display_name) < len(sg_map[pk]["Studiengang"]):
            sg_map[pk] = {
                "Produktkuerzel": pk,
                "Studiengang": display_name,
                "Hochschulbereich": r["Hochschulbereich"],
                "HochschulbereichKuerzel": r["HochschulbereichKuerzel"],
                "Abschluss": r.get("Abschluss") or ("Master" if pk.startswith("M") else "Bachelor"),
            }

    stud_map = merged_stud

    # Nach HSB gruppieren
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

    for hsb in hsb_map.values():
        hsb["programmes"].sort(key=lambda p: p["name"])

    HSB_ORDER = config_db.HSB_ORDER
    data = sorted(hsb_map.values(), key=lambda h: HSB_ORDER.get(h["kuerzel"], 99))
    cache_set("studiengaenge", data)
    return data


# ===================================================================
# trends
# ===================================================================


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

    # Aktuellster Wert + Delta
    if zeitreihe_ws[0]:
        aktuell = zeitreihe_ws[0]
        vorher = zeitreihe_ws[1] if len(zeitreihe_ws) >= 2 else 0
    else:
        aktuell = zeitreihe_ss[0] if zeitreihe_ss else 0
        vorher = zeitreihe_ss[1] if len(zeitreihe_ss) >= 2 else 0
    diff = aktuell - vorher
    pct = f"{(diff / vorher * 100):.1f}".replace(".", ",") if vorher else "0,0"
    sign = "+" if diff >= 0 else ""
    delta_str = f"{sign}{diff} ({sign}{pct}%)"

    # Beginner Delta
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
    b_delta = f"{b_sign}{b_diff} ({b_sign}{b_pct}%)"

    # HSZ-Daten
    hsz_data: dict = {}
    for r in hsz_rows:
        hsz = r["Hochschulzentrum"]
        jahr = r["Jahr"]
        if hsz not in hsz_data:
            hsz_data[hsz] = {}
        if jahr not in hsz_data[hsz]:
            hsz_data[hsz][jahr] = {
                "ss": 0,
                "ws": 0,
                "beginner_ss": 0,
                "beginner_ws": 0,
                "avg_ss": 0,
                "avg_ws": 0,
                "avg_beginner_ss": 0,
                "avg_beginner_ws": 0,
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
        [
            (sql_alter, p_alter),
            (sql_detail, p_detail),
            (sql_beruf_a, p_beruf_a),
        ]
    )

    def pct(val, total):
        return round(int(val or 0) / max(int(total or 0), 1) * 100, 1)

    def detail_block(r):
        if not r:
            return (
                {"weiblich": 0, "maennlich": 0},
                {"inlaendisch": 0, "auslaendisch": 0, "dueh": 0},
                {"dual": 0, "tagesstudium": 0, "nein": 0},
                {"ja": 0, "nein": 0},
            )
        t = int(r["Total"] or 1)
        geschlecht = {
            "weiblich": pct(r["Weiblich"], t),
            "maennlich": pct(r["Maennlich"], t),
        }
        inl = int(r.get("Inlaendisch", 0) or 0)
        ausl = int(r.get("Auslaendisch", 0) or 0)
        unbek = int(r.get("Unbekannt", 0) or 0)
        staatsang = {
            "inlaendisch": pct(inl, t),
            "auslaendisch": pct(ausl, t),
            "dueh": pct(unbek, t),
        }
        dual_v = int(r.get("Dual", 0) or 0)
        tages = int(r.get("Tagesstudium", 0) or 0)
        dual = {
            "dual": pct(dual_v, t),
            "tagesstudium": pct(tages, t),
            "nein": pct(t - dual_v - tages, t),
        }
        offene_v = int(r.get("OffeneHochschule", 0) or 0)
        intern = {"ja": pct(offene_v, t), "nein": pct(t - offene_v, t)}
        return geschlecht, staatsang, dual, intern

    def sum_detail_rows(rows_list):
        if not rows_list:
            return None
        agg = {
            "Total": 0,
            "Weiblich": 0,
            "Maennlich": 0,
            "Inlaendisch": 0,
            "Auslaendisch": 0,
            "Unbekannt": 0,
            "Dual": 0,
            "Tagesstudium": 0,
            "OffeneHochschule": 0,
        }
        for r in rows_list:
            for k in agg:
                agg[k] += int(r.get(k, 0) or 0)
        return agg

    # Alter: weighted average per semester
    sem_alter: dict = {}
    for r in alter_rows:
        sk = r["Semesterkuerzel"]
        avg_val = float(r["DurchschnittsAlter"]) if r["DurchschnittsAlter"] else None
        cnt = int(r["Cnt"] or 0)
        if avg_val is not None and cnt > 0:
            if sk not in sem_alter:
                sem_alter[sk] = {"sum": 0, "cnt": 0}
            sem_alter[sk]["sum"] += avg_val * cnt
            sem_alter[sk]["cnt"] += cnt
    alter_overall = [
        {"Semesterkuerzel": sk, "DurchschnittsAlter": d["sum"] / d["cnt"]}
        for sk, d in sorted(sem_alter.items())
        if d["cnt"] > 0
    ]
    alter_rows_filtered = _semester_filter_7(alter_overall)
    alter_semester = [_fmt_sem(r["Semesterkuerzel"]) for r in alter_rows_filtered]
    alter_werte = [round(float(r["DurchschnittsAlter"]), 1) for r in alter_rows_filtered]

    # Detail: sum across HSZ per Zeitraum
    aktuell = sum_detail_rows([r for r in detail_rows if r["Zeitraum"] == "aktuell"])
    rest = sum_detail_rows([r for r in detail_rows if r["Zeitraum"] == "rest"])
    g_akt, s_akt, d_akt, i_akt = detail_block(aktuell)
    g_rest, s_rest, d_rest, i_rest = detail_block(rest)

    # Berufsausbildungen
    beruf_agg: dict = {}
    for r in beruf_rows:
        key = (r["Zeitraum"], r["Berufsausbildung"])
        beruf_agg[key] = beruf_agg.get(key, 0) + int(r["Cnt"])
    beruf_akt = sorted(
        [(ba, cnt) for (z, ba), cnt in beruf_agg.items() if z == "aktuell"],
        key=lambda x: -x[1],
    )
    beruf_rest = sorted(
        [(ba, cnt) for (z, ba), cnt in beruf_agg.items() if z == "rest"],
        key=lambda x: -x[1],
    )
    total_akt = sum(cnt for _, cnt in beruf_akt) or 1
    total_rest = sum(cnt for _, cnt in beruf_rest) or 1

    # Per-HSZ
    hsz_set_s = sorted(
        set(r.get("HSZ") for r in alter_rows if r.get("HSZ"))
        | set(r.get("HSZ") for r in detail_rows if r.get("HSZ"))
    )
    hsz_detail: dict = {}
    for hsz in hsz_set_s:
        h_alter = [r for r in alter_rows if r.get("HSZ") == hsz]
        h_alter_filtered = _semester_filter_7(h_alter)
        h_alter_semester = [_fmt_sem(r["Semesterkuerzel"]) for r in h_alter_filtered]
        h_alter_werte = [
            round(float(r["DurchschnittsAlter"]), 1) if r["DurchschnittsAlter"] else None
            for r in h_alter_filtered
        ]
        h_aktuell = sum_detail_rows(
            [r for r in detail_rows if r["Zeitraum"] == "aktuell" and r.get("HSZ") == hsz]
        )
        h_rest = sum_detail_rows(
            [r for r in detail_rows if r["Zeitraum"] == "rest" and r.get("HSZ") == hsz]
        )
        h_g_akt, h_s_akt, h_d_akt, h_i_akt = detail_block(h_aktuell)
        h_g_rest, h_s_rest, h_d_rest, h_i_rest = detail_block(h_rest)
        h_beruf_akt = sorted(
            [
                (r["Berufsausbildung"], int(r["Cnt"]))
                for r in beruf_rows
                if r["Zeitraum"] == "aktuell" and r.get("HSZ") == hsz
            ],
            key=lambda x: -x[1],
        )
        h_beruf_rest = sorted(
            [
                (r["Berufsausbildung"], int(r["Cnt"]))
                for r in beruf_rows
                if r["Zeitraum"] == "rest" and r.get("HSZ") == hsz
            ],
            key=lambda x: -x[1],
        )
        h_total_akt = sum(cnt for _, cnt in h_beruf_akt) or 1
        h_total_rest = sum(cnt for _, cnt in h_beruf_rest) or 1
        hsz_detail[hsz] = {
            "alter_zeitreihe_semester": h_alter_semester,
            "alter_zeitreihe": h_alter_werte,
            "top_berufsausbildungen_aktuell": [
                {"name": ba, "pct": round(cnt / h_total_akt * 100, 1)}
                for ba, cnt in h_beruf_akt[:5]
            ],
            "top_berufsausbildungen_rest": [
                {"name": ba, "pct": round(cnt / h_total_rest * 100, 1)}
                for ba, cnt in h_beruf_rest[:5]
            ],
            "geschlecht_aktuell": h_g_akt,
            "geschlecht_rest": h_g_rest,
            "staatsang_aktuell": h_s_akt,
            "staatsang_rest": h_s_rest,
            "dual_aktuell": h_d_akt,
            "dual_rest": h_d_rest,
            "intern_aktuell": h_i_akt,
            "intern_rest": h_i_rest,
        }

    data = {
        "alter_zeitreihe_semester": alter_semester,
        "alter_zeitreihe": alter_werte,
        "top_berufsausbildungen_aktuell": [
            {"name": ba, "pct": round(cnt / total_akt * 100, 1)} for ba, cnt in beruf_akt[:5]
        ],
        "top_berufsausbildungen_rest": [
            {"name": ba, "pct": round(cnt / total_rest * 100, 1)} for ba, cnt in beruf_rest[:5]
        ],
        "geschlecht_aktuell": g_akt,
        "geschlecht_rest": g_rest,
        "staatsang_aktuell": s_akt,
        "staatsang_rest": s_rest,
        "dual_aktuell": d_akt,
        "dual_rest": d_rest,
        "intern_aktuell": i_akt,
        "intern_rest": i_rest,
        "hsz_detail": hsz_detail,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# studienerfolg
# ===================================================================


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

    # FOM-weite Queries global cachen
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
    fs_sg, vl_sg = query_db_multi(
        [
            (sql_fs, p_fs),
            (sql_vl, p_vl),
        ]
    )

    # Fachsemester Labels
    fs_labels_num = sorted(
        set(r["Fachsem"] for r in fs_sg if r["Fachsem"] not in ("0",)),
        key=lambda x: 99 if x == "9+" else int(x),
    )
    fs_labels = [f"{lbl}. FS" if lbl != "9+" else "9+" for lbl in fs_labels_num]
    fs_labels += [
        "Abbrecher",
        "Wechsler",
        "aktiv\n(regulaer)",
        "aktiv\n(Verlaengerung)",
        "Absolventen",
    ]

    def calc_fachsem_pct(rows, labels_num):
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

        def cluster_total(name, rsz_filter=None):
            t = 0
            for lbl in labels_num:
                cd = pivot.get(lbl, {}).get(name, {})
                t += cd.get(rsz_filter, 0) if rsz_filter is not None else sum(cd.values())
            return t

        result = []
        for lbl in labels_num:
            abbrecher_fs = sum(pivot.get(lbl, {}).get("Abbrecher", {}).values())
            result.append(round(abbrecher_fs / kohortengroesse * 100, 1))

        result.append(round(cluster_total("Abbrecher") / kohortengroesse * 100, 1))
        result.append(round(cluster_total("Wechsler") / kohortengroesse * 100, 1))
        result.append(round(cluster_total("Eingeschrieben", 0) / kohortengroesse * 100, 1))
        result.append(round(cluster_total("Eingeschrieben", 1) / kohortengroesse * 100, 1))
        result.append(round(cluster_total("Absolvent") / kohortengroesse * 100, 1))
        return result

    # Aggregate fs_sg across HSZ for overall
    fs_sg_agg: dict = {}
    for r in fs_sg:
        key = (r["Fachsem"], r["AusstiegsCluster"], int(r["RSZ"]))
        fs_sg_agg[key] = fs_sg_agg.get(key, 0) + int(r["Anzahl"])
    fs_sg_overall = [
        {"Fachsem": k[0], "AusstiegsCluster": k[1], "RSZ": k[2], "Anzahl": v}
        for k, v in fs_sg_agg.items()
    ]

    sg_pcts = calc_fachsem_pct(fs_sg_overall, fs_labels_num)
    fom_pcts = calc_fachsem_pct(fs_fom, fs_labels_num)

    # Verlaengerungssemester
    def calc_verlaengerung(rows):
        pivot: dict = {}
        for r in rows:
            sv = int(r["VerlaengerungsSem"])
            if sv < 0:
                sv = 0
            key = "9+" if sv > 8 else str(sv)
            pivot[key] = pivot.get(key, 0) + int(r["Anzahl"])
        return pivot

    vl_sg_agg: dict = {}
    for r in vl_sg:
        sv = int(r["VerlaengerungsSem"])
        if sv < 0:
            sv = 0
        key = "9+" if sv > 8 else str(sv)
        vl_sg_agg[key] = vl_sg_agg.get(key, 0) + int(r["Anzahl"])
    vl_sg_pivot = vl_sg_agg
    vl_fom_pivot = calc_verlaengerung(vl_fom)

    def sort_key(x):
        return 99 if x == "9+" else int(x)

    all_sv = sorted(set(list(vl_sg_pivot.keys()) + list(vl_fom_pivot.keys())), key=sort_key)
    vl_labels = [
        "Regelstudienzeit" if sv == "0" else (f"{sv} VS" if sv == "9+" else f"{sv}. VS")
        for sv in all_sv
    ]

    vl_sg_vals = [vl_sg_pivot.get(sv, 0) for sv in all_sv]
    vl_fom_vals = [vl_fom_pivot.get(sv, 0) for sv in all_sv]
    vl_pct = [
        round(vl_sg_pivot.get(sv, 0) / max(vl_fom_pivot.get(sv, 0), 1) * 100, 1) for sv in all_sv
    ]

    # Per-HSZ
    hsz_set_se = sorted(
        set(r.get("HSZ") for r in fs_sg if r.get("HSZ"))
        | set(r.get("HSZ") for r in vl_sg if r.get("HSZ"))
    )
    hsz_detail: dict = {}
    for hsz in hsz_set_se:
        h_fs = [r for r in fs_sg if r.get("HSZ") == hsz]
        h_vl = [r for r in vl_sg if r.get("HSZ") == hsz]
        h_sg_pcts = calc_fachsem_pct(h_fs, fs_labels_num)
        h_vl_pivot = calc_verlaengerung(h_vl)
        h_vl_vals = [h_vl_pivot.get(sv, 0) for sv in all_sv]
        hsz_detail[hsz] = {
            "fachsemester_sg": h_sg_pcts,
            "verlaengerung_sg": h_vl_vals,
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


def _compute_uebergang_stats(
    rows: list[dict], kohorten_set: list[str]
) -> tuple[dict, dict]:
    """Berechnet detaillierte Uebergangs-Statistiken pro Kohorte."""
    per_kohorte: dict = {}
    master_sg_per_kohorte: dict = {}

    for kohorte in kohorten_set:
        kohorte_rows = [r for r in rows if str(r.get("B_Kohorte")) == kohorte]

        # Pro Person: besten Eintrag bestimmen (frueheste Master-Einschreibung)
        persons: dict = {}
        for r in kohorte_rows:
            pid = r.get("PersonenFID")
            if pid not in persons:
                persons[pid] = r
            else:
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
                sum(per_kohorte[k]["counts"][kat] for kat in kats)
                / per_kohorte[k]["total"]
                * 100,
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
                    master_sg_per_kohorte.get(k, {}).get(sg, 0)
                    / per_kohorte[k]["total"]
                    * 100,
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
        return round(
            sum(per_kohorte[k]["counts"][kat] for k in kohorten_set) / total_all * 100, 1
        )

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
    uebersicht_gruppen = [
        None,
        "am jetzigen HSZ",
        "am jetzigen HSZ",
        "am jetzigen HSZ",
        "an anderem HSZ",
        "an anderem HSZ",
        "an anderem HSZ",
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

    # FOM-weite Herkunft cachen
    fom_rows = cache_get("_global_herkunft_fom")
    if not fom_rows:
        fom_rows = query_db(queries.SQL_HERKUNFT_FOM)
        cache_set("_global_herkunft_fom", fom_rows)

    def classify(row):
        """Klassifiziert Herkunft: am_jetzigen_vorher/nachher, an_anderem_vorher/nachher."""
        same_hsz = row.get("GleicherHSZ") == 1
        b_ex = row.get("B_ExDatum")
        m_im = row.get("M_ImDatum")
        if b_ex and m_im:
            timing = "vorher" if str(b_ex) <= str(m_im) else "nachher"
        else:
            timing = "vorher"
        prefix = "am_jetzigen" if same_hsz else "an_anderem"
        return f"{prefix}_{timing}"

    def compute_herkunft_stats(data_rows):
        total = len(data_rows) or 1
        # Bachelor-Studiengaenge
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

            cat = classify(r)
            uebersicht[cat] = uebersicht.get(cat, 0) + 1

        def top10(d):
            return sorted(d.items(), key=lambda x: -x[1])[:10]

        bachelor_studiengaenge = [
            {"name": sg, "pct": round(cnt / total * 100, 1)} for sg, cnt in top10(sg_counts)
        ]
        bachelor_studiengaenge_gleich = [
            {"name": sg, "pct": round(cnt / total * 100, 1)} for sg, cnt in top10(sg_gleich)
        ]
        bachelor_studiengaenge_anders = [
            {"name": sg, "pct": round(cnt / total * 100, 1)} for sg, cnt in top10(sg_anders)
        ]
        top_studienrichtungen = [
            {"name": sr, "pct": round(cnt / total * 100, 1)} for sr, cnt in top10(studienrichtungen)
        ]
        top_studienrichtungen_gleich = [
            {"name": sr, "pct": round(cnt / total * 100, 1)}
            for sr, cnt in top10(studienrichtungen_gleich)
        ]
        top_studienrichtungen_anders = [
            {"name": sr, "pct": round(cnt / total * 100, 1)}
            for sr, cnt in top10(studienrichtungen_anders)
        ]

        uebersicht_labels = [
            "am jetzigen HSZ\n(vorher)",
            "am jetzigen HSZ\n(nachher)",
            "an anderem HSZ\n(vorher)",
            "an anderem HSZ\n(nachher)",
        ]
        uebersicht_keys = [
            "am_jetzigen_vorher",
            "am_jetzigen_nachher",
            "an_anderem_vorher",
            "an_anderem_nachher",
        ]
        uebersicht_vals = [round(uebersicht.get(k, 0) / total * 100, 1) for k in uebersicht_keys]

        return {
            "bachelor_studiengaenge": bachelor_studiengaenge,
            "bachelor_studiengaenge_gleich": bachelor_studiengaenge_gleich,
            "bachelor_studiengaenge_anders": bachelor_studiengaenge_anders,
            "top_studienrichtungen": top_studienrichtungen,
            "top_studienrichtungen_gleich": top_studienrichtungen_gleich,
            "top_studienrichtungen_anders": top_studienrichtungen_anders,
            "uebersicht_labels": uebersicht_labels,
            "uebersicht_vals": uebersicht_vals,
        }

    sg_stats = compute_herkunft_stats(rows)
    fom_stats = compute_herkunft_stats(fom_rows)

    # HSZ-Detail
    hsz_set = sorted(set(r.get("M_HSZ") for r in rows if r.get("M_HSZ")))
    hsz_detail: dict = {}
    for hsz in hsz_set:
        h_rows = [r for r in rows if r.get("M_HSZ") == hsz]
        hsz_detail[hsz] = compute_herkunft_stats(h_rows)

    data = {
        **sg_stats,
        "uebersicht_gruppen": sg_stats["uebersicht_labels"],
        "uebersicht_fom": fom_stats["uebersicht_vals"],
        "uebersicht_sg": sg_stats["uebersicht_vals"],
        "hsz_detail": hsz_detail,
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
        gesamt = sum(int(r.get("Gesamtstudierende", 0) or 0) for r in sem_rows)
        zuz = sum(int(r.get("Zuzahler", 0) or 0) for r in sem_rows)
        sg_gesamt.append(gesamt)
        sg_zuzahler.append(zuz)
        sg_pct.append(round(zuz / max(gesamt, 1) * 100, 1))

    # FOM-Daten
    fom_pct = []
    for sem in semester:
        fom_sem = [r for r in zuz_fom_filtered if r["Semesterkuerzel"] == sem]
        gesamt = sum(int(r.get("Gesamtstudierende", 0) or 0) for r in fom_sem)
        zuz = sum(int(r.get("Zuzahler", 0) or 0) for r in fom_sem)
        fom_pct.append(round(zuz / max(gesamt, 1) * 100, 1))

    data = {
        "semester": semester_labels,
        "sg_gesamt": sg_gesamt,
        "sg_zuzahler": sg_zuzahler,
        "sg_pct": sg_pct,
        "fom_pct": fom_pct,
    }
    cache_set(cache_key, data)
    return data


# ===================================================================
# vertiefungsrichtungen
# ===================================================================


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

    def build_table(filtered_rows, semesters):
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

    # VR und WP trennen
    vr_rows = [r for r in rows if r.get("Wahlart") == "Vertiefungsrichtung"]
    wp_rows = [r for r in rows if r.get("Wahlart") != "Vertiefungsrichtung"]

    data: dict = {"semester": semester_labels}

    if vr_rows:
        vr_items, vr_gesamt = build_table(vr_rows, all_semesters)
        data["vr_semester"] = semester_labels
        data["vr_module"] = vr_items
        data["vr_gesamt"] = vr_gesamt

    if wp_rows:
        wp_items, wp_gesamt = build_table(wp_rows, all_semesters)
        data["wp_semester"] = semester_labels
        data["wp_module"] = wp_items
        data["wp_gesamt"] = wp_gesamt

    # Hochschulzertifikate
    try:
        sql_hz, p_hz = pk_expand_sql(queries.SQL_HOCHSCHULZERTIFIKATE, produktkuerzel, count=1)
        hz_rows = query_db(sql_hz, p_hz)
        if hz_rows:
            hz_blocks = sorted(set(r["Block"] for r in hz_rows if r["Block"]))
            hz_names = sorted(set(r["Zertifikat"] for r in hz_rows))
            hz_items = []
            for name in hz_names:
                vals = []
                for block in hz_blocks:
                    cnt = sum(
                        int(r.get("Anzahl", 0) or 0)
                        for r in hz_rows
                        if r["Zertifikat"] == name and r["Block"] == block
                    )
                    vals.append(cnt)
                hz_items.append({"name": name, "werte": vals})
            data["hz_blocks"] = hz_blocks
            data["hz_zertifikate"] = hz_items
    except Exception:
        pass

    cache_set(cache_key, data)
    return data


# ===================================================================
# rahmendaten
# ===================================================================


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

    # UE-Verteilung
    ue: dict = {}
    ue_by_semester: dict = {}
    try:
        variants = expand_pk(produktkuerzel)
        ph_buchungen = ",".join("?" * len(variants))
        sql_parts = queries.SQL_UES.split("= ?")
        sql_ues_final = sql_parts[0] + "= ?" + sql_parts[1] + f"IN ({ph_buchungen})" + sql_parts[2]
        p_ues = [produktkuerzel] + variants
        ue_rows = query_db(sql_ues_final, p_ues)

        # Module ohne Fachsemester per VP-Aliases und Grow nachschlagen
        all_modules = set()
        modules_without_sem = set()
        for r in ue_rows:
            mod_id = int(r["ModulFID"]) if r["ModulFID"] else None
            if mod_id:
                all_modules.add(mod_id)
                if r["Fachsemester"] is None:
                    modules_without_sem.add(mod_id)

        # VP-Aliases Lookup
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

        # Grow Lookup fuer verbleibende
        grow_mapping: dict = {}
        still_missing = modules_without_sem - set(vp_aliases_mapping.keys())
        if still_missing:
            ph_grow = ",".join("?" * len(still_missing))
            sql_grow = queries.SQL_GROW_SEMESTER.replace("{placeholders}", ph_grow)
            grow_rows = query_db(sql_grow, list(still_missing))
            for r in grow_rows:
                grow_mapping[int(r["ModulID"])] = int(r["Fachsemester"])

        # UE nach Fachsemester und Typ aggregieren
        for r in ue_rows:
            typ = r["UETyp"]
            val = int(r["TotalUE"] or 0)
            if typ not in ("praxis", "virtuell", "folgt"):
                continue
            modul_id = int(r["ModulFID"]) if r["ModulFID"] else None
            sem_vp = int(r["Fachsemester"]) if r["Fachsemester"] is not None else None
            sem_aliases = vp_aliases_mapping.get(modul_id) if modul_id else None
            sem_grow = grow_mapping.get(modul_id) if modul_id else None
            sem = (
                sem_vp
                if sem_vp is not None
                else (sem_aliases if sem_aliases is not None else sem_grow)
            )
            sem_key = int(sem) if sem is not None else 0

            ue[typ] = ue.get(typ, 0) + val
            ue_by_semester.setdefault(sem_key, {})
            ue_by_semester[sem_key][typ] = ue_by_semester[sem_key].get(typ, 0) + val
    except Exception:
        pass

    # Dekan + Akkreditierung aus Excel-Mapping (falls vorhanden)
    dekan = ""
    akkred = ""

    data = {
        "imAngebotSeit": im_angebot_seit,
        "zeitmodelle": zeitmodelle,
        "studienformate": studienformate,
        "akkreditierungsDatum": akkred,
        "verantwortlicherDekan": dekan,
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

    Args:
        produktkuerzel: Basis-Produktkuerzel des Studiengangs.

    Returns:
        Dict mit Anrechnungs-Daten.

    Note:
        Diese Funktion verwendet Temp-Tabellen und muss daher direkt auf der
        DB-Connection arbeiten. Die komplexe Logik mit #gs_anr, #anr_data,
        #antrag_qual wird in einem einzigen Connection-Kontext ausgefuehrt.
    """
    from studiengang_steckbriefe.services.db_connector import (
        get_connection,
        release_connection,
    )

    cache_key = f"anrechnungen_{produktkuerzel}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    variants = expand_pk(produktkuerzel)
    pk_placeholders = ",".join("?" * len(variants))

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1) Population: Alle Beginner/Quereinsteiger im Zeitraum inkl. AnrechnungsGrund
        #    Quelle: se.AnrechnungsGrund auf StudienEintraege (keine separate Anrechnungen-Tabelle noetig)
        try:
            cursor.execute("DROP TABLE IF EXISTS #gs_anr")
        except Exception:
            pass
        cursor.execute(
            f"""
            SELECT DISTINCT se.PersonenFID, se.StudienEintragID, l.Hochschulzentrum AS HSZ,
                   se.AnrechnungsGrund
            INTO #gs_anr
            FROM BCW_DWH.dwh.StudierendenStatusJeSemester sz
                INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sz.StudienEintragFID
                INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
                INNER JOIN BCW_DWH.dwh.StatusGruppen sg ON sg.Status = sz.Status
            WHERE sg.StatusGruppe IN ('{config_db.get_param("anrechnungen", "statusgruppe_1", "Beginner mit UV")}',
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
        """,
            variants,
        )

        # 2) Kennzahlen direkt aus #gs_anr berechnen
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT StudienEintragID) AS Total,
                -- mit Anrechnung = AnrechnungsGrund vorhanden
                COUNT(DISTINCT CASE WHEN AnrechnungsGrund IS NOT NULL
                                         AND LTRIM(RTRIM(AnrechnungsGrund)) <> ''
                                    THEN StudienEintragID END) AS MitAnrechnung,
                -- berufliche Qualifikation = Offene Hochschule (berufliche Vorkenntnisse)
                COUNT(DISTINCT CASE WHEN AnrechnungsGrund IN ({config_db.OFFENE_HOCHSCHULE_SQL})
                                    THEN StudienEintragID END) AS Beruflich,
                -- hochschulische Qualifikation = vorhanden, aber NICHT beruflich
                COUNT(DISTINCT CASE WHEN AnrechnungsGrund IS NOT NULL
                                         AND LTRIM(RTRIM(AnrechnungsGrund)) <> ''
                                         AND AnrechnungsGrund NOT IN ({config_db.OFFENE_HOCHSCHULE_SQL})
                                    THEN StudienEintragID END) AS Hochschulisch,
                -- keine Anrechnung
                COUNT(DISTINCT CASE WHEN AnrechnungsGrund IS NULL
                                         OR LTRIM(RTRIM(AnrechnungsGrund)) = ''
                                    THEN StudienEintragID END) AS Keine
            FROM #gs_anr
        """)
        s = dict(zip([c[0] for c in cursor.description], cursor.fetchone(), strict=False))
        total = max(int(s.get("Total", 0) or 0), 1)
        mit_anrechnung = int(s.get("MitAnrechnung", 0) or 0)
        anteil_pct = round(mit_anrechnung / total * 100, 1)
        beruflich_abs = int(s.get("Beruflich", 0) or 0)
        hochschulisch_abs = int(s.get("Hochschulisch", 0) or 0)
        hs_ber_abs = 0  # AnrechnungsGrund ist einwertig, hs+ber gleichzeitig nicht moeglich
        keine_abs = int(s.get("Keine", 0) or 0)
        hochschulisch_pct = round(hochschulisch_abs / total * 100, 1)
        beruflich_pct = round(beruflich_abs / total * 100, 1)
        hs_ber_pct = 0.0
        keine_pct = round(keine_abs / total * 100, 1)
        offene_hs_pct = beruflich_pct  # Offene Hochschule = berufliche Qualifikation
        top_module: list = []  # Keine Einzel-Anrechnungszeilen verfuegbar

        # Aufraeumen
        try:
            cursor.execute("DROP TABLE IF EXISTS #gs_anr")
        except Exception:
            pass

    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    else:
        release_connection(conn)

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
        "top_module": [{"name": m["Name"], "anzahl": int(m["Cnt"])} for m in top_module],
    }
    cache_set(cache_key, data)
    return data
