"""SQL-Query-Builder und -Templates fuer Studiengang-Steckbriefe.

Dieses Modul generiert alle SQL-Queries dynamisch aus der Konfigurations-DB.
Die Queries werden beim Start und bei Config-Reload neu gebaut.
"""

from __future__ import annotations

import sys

from studiengang_steckbriefe.services import config_db

# Globale SQL-Variablen (werden durch build_sql_queries() gesetzt)
SQL_STUDIERENDE_ZEITREIHE: str = ""
SQL_STUDIERENDE_HSZ: str = ""
SQL_STUDIERENDE_HSZ_AVG: str = ""
SQL_AKTIVE_HSZEN: str = ""
SQL_STUDIENGAENGE_LISTE: str = ""
SQL_STUDIERENDE_AKTUELL: str = ""
SQL_STAMMDATEN_ALTER: str = ""
SQL_STAMMDATEN_DETAIL: str = ""
SQL_STAMMDATEN_BERUFSAUSBILDUNG: str = ""
SQL_FACHSEMESTER: str = ""
SQL_FACHSEMESTER_FOM: str = ""
SQL_VERLAENGERUNG: str = ""
SQL_VERLAENGERUNG_FOM: str = ""
SQL_UEBERGANG: str = ""
SQL_UEBERGANG_FOM: str = ""
SQL_HERKUNFT: str = ""
SQL_HERKUNFT_FOM: str = ""
SQL_ZUZAHLER: str = ""
SQL_ZUZAHLER_FOM: str = ""
SQL_ZUZAHLER_TOP10: str = ""
SQL_VERTIEFUNGSRICHTUNGEN: str = ""
SQL_HOCHSCHULZERTIFIKATE: str = ""
SQL_RAHMENDATEN: str = ""
SQL_STUDIENFORMATE: str = ""
SQL_UES: str = ""
SQL_VP_ALIASES_SEMESTER: str = ""
SQL_GROW_SEMESTER: str = ""
SQL_ANRECHNUNGEN_ANTEIL: str = ""
SQL_ANRECHNUNGEN_OFFENE_HS: str = ""
_PK_CASE: str = ""

# Statusgruppen-Konstanten (vermeiden duplizierter Literale)
_SG_GESAMTSTUDIERENDE = "Gesamtstudierende mit UV"
_SG_BEGINNER = "Beginner mit UV"
_SG_QUEREINSTEIGER = "Quereinsteiger mit UV"


def _build_sql_queries():
    """Baut alle SQL-Queries mit Werten aus der Konfigurations-DB."""
    global SQL_STUDIERENDE_ZEITREIHE, SQL_STUDIERENDE_HSZ, SQL_STUDIERENDE_HSZ_AVG, SQL_AKTIVE_HSZEN
    global SQL_STUDIENGAENGE_LISTE, SQL_STUDIERENDE_AKTUELL

    _excl = config_db.EXCLUDED_HSZ_SQL
    _pk_case_s = config_db._build_pk_case_for_s()
    _jahre_trends = config_db.get_param_int("trends", "jahre_zurueck", 4)
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
      AND s.Ausrichtung = 'national'
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
      AND s.Ausrichtung = 'national'
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
      AND s.Ausrichtung = 'national'
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
          AND s.Ausrichtung = 'national'
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
          AND s.Ausrichtung = 'national'
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
      AND s.Ausrichtung = 'national'
      AND s.Hochschulzentrum NOT IN ({_excl})
      AND s.Semesterkuerzel = CONCAT(YEAR(GETDATE()), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    GROUP BY s.Produktkuerzel
"""

    # ─── PK-Mapping für Studiengangvarianten → Basis-Produktkuerzel ───
    global _PK_CASE
    _PK_CASE = config_db.PK_CASE_SQL

    # Verbleibende Queries mit dynamischen Config-Werten
    global SQL_STAMMDATEN_ALTER

    _jahre_stamm = config_db.get_param_int("stammdaten", "jahre_zurueck", 2)
    _kohorten_j = config_db.get_param_int("studienerfolg", "kohorten_jahre", 5)
    _uebergang_j = config_db.get_param_int("uebergang", "kohorten_jahre", 5)
    _herkunft_j = config_db.get_param_int("herkunft", "kohorten_jahre", 5)
    _vertiefung_von = config_db.get_param("vertiefung", "datum_von", "2018-09-01")
    _vertiefung_bis = config_db.get_param("vertiefung", "datum_bis", "2021-09-01")
    _hz_von = config_db.get_param("hochschulzertifikate", "datum_von", "2021-08-01")
    _jahre_zuz = config_db.get_param_int("zuzahler", "jahre_zurueck", 4)
    _sem_anr = config_db.get_param_int("anrechnungen", "semester_zurueck", 6)
    _sg_trends = config_db.get_param("trends", "statusgruppe", _SG_GESAMTSTUDIERENDE)
    _sg_stamm_1 = config_db.get_param("stammdaten", "statusgruppe", _SG_BEGINNER)
    _sg_stamm_2 = config_db.get_param("stammdaten", "statusgruppe_2", _SG_QUEREINSTEIGER)
    _sg_zuz = config_db.get_param("zuzahler", "statusgruppe", _SG_GESAMTSTUDIERENDE)
    _sg_anr_1 = config_db.get_param("anrechnungen", "statusgruppe_1", _SG_BEGINNER)
    _sg_anr_2 = config_db.get_param("anrechnungen", "statusgruppe_2", _SG_QUEREINSTEIGER)
    _offene_hs = config_db.OFFENE_HOCHSCHULE_SQL
    _ue_raumids = config_db.get_filter_sql("UE_RAUMID")
    _ue_veransttyp = config_db.get_filter_sql("UE_VERANSTTYP")
    _ue_produktgruppe = config_db.get_filter_sql("UE_PRODUKTGRUPPE")
    _ue_statusrpl = config_db.get_filter_sql("UE_STATUSRPL")
    _vertiefung_art = config_db.get_filter_sql("VERTIEFUNG_ART")
    _vertiefung_fach_excl = config_db.get_filter_sql("VERTIEFUNG_FACH")
    _leistungsart_ignore = config_db.get_filter_sql("LEISTUNGSART_IGNORE")
    _zuzahler_empf = config_db.get_filter_sql("ZUZAHLER_EMPF")
    _zuzahler_kostentyp = (
        config_db.get_filter_values("ZUZAHLER_KOSTENTYP")[0]
        if config_db.get_filter_values("ZUZAHLER_KOSTENTYP")
        else "Arbeitgeber"
    )
    _dual_format = config_db.get_filter_sql("DUAL_STUDIENFORMAT")
    _dual_bildung = (
        config_db.get_filter_values("DUAL_BILDUNGSABSCHNITT")[0]
        if config_db.get_filter_values("DUAL_BILDUNGSABSCHNITT")
        else "Erstausbildung"
    )

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

SQL_FACHSEMESTER = (
    _SE_CTE
    + """
    SELECT
        CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END AS Fachsem,
"""
    + _SE_CLUSTER_CASE
    + """ AS AusstiegsCluster,
"""
    + _SE_RSZ_CASE
    + """ AS RSZ,
        Hochschulzentrum AS HSZ,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = ?
"""
    + _SE_KOHORTE_FILTER
    + """
    GROUP BY CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END,
"""
    + _SE_CLUSTER_CASE
    + """,
"""
    + _SE_RSZ_CASE
    + """,
        Hochschulzentrum
    ORDER BY Fachsem
"""
)

SQL_FACHSEMESTER_FOM = (
    _SE_CTE
    + """
    SELECT
        CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END AS Fachsem,
"""
    + _SE_CLUSTER_CASE
    + """ AS AusstiegsCluster,
"""
    + _SE_RSZ_CASE
    + """ AS RSZ,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1
"""
    + _SE_KOHORTE_FILTER
    + """
    GROUP BY CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END,
"""
    + _SE_CLUSTER_CASE
    + """,
"""
    + _SE_RSZ_CASE
    + """
    ORDER BY Fachsem
"""
)

SQL_VERLAENGERUNG = (
    _SE_CTE
    + """
    SELECT
        CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT) AS VerlaengerungsSem,
        Hochschulzentrum AS HSZ,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = ?
      AND Ausstiegsstatus = 'A'
"""
    + _SE_KOHORTE_FILTER
    + """
    GROUP BY CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT),
        Hochschulzentrum
    ORDER BY VerlaengerungsSem
"""
)

SQL_VERLAENGERUNG_FOM = (
    _SE_CTE
    + """
    SELECT
        CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT) AS VerlaengerungsSem,
        COUNT(*) AS Anzahl
    FROM LatestStatus
    WHERE rn = 1
      AND Ausstiegsstatus = 'A'
"""
    + _SE_KOHORTE_FILTER
    + """
    GROUP BY CAST(ROUND(DATEDIFF(MONTH, LehrgangsEnde, ExmatrikulationsDatum) / 6.0 + 0.4, 0) AS INT)
    ORDER BY VerlaengerungsSem
"""
)

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
        ba.B_PK, ba.B_SG, ba.B_Familie, ba.B_HSZ_K, ba.B_HSZ, ba.B_ExDatum,
        CASE WHEN mb.M_HSZ_K = ba.B_HSZ_K THEN 1 ELSE 0 END AS GleicherHSZ
    FROM master_beginner mb
        LEFT JOIN bachelor_abschluss ba ON ba.PersonenFID = mb.PersonenFID
            AND ba.B_ImDatum < mb.M_ImDatum
"""

SQL_HERKUNFT_FOM = """
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
        ba.B_PK, ba.B_SG, ba.B_Familie, ba.B_HSZ_K, ba.B_HSZ, ba.B_ExDatum,
        CASE WHEN mb.M_HSZ_K = ba.B_HSZ_K THEN 1 ELSE 0 END AS GleicherHSZ
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
    gs_cte = _ZUZAHLER_GS_CTE.replace("{pk_filter}", pk_filter_clause)
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
    module = sys.modules[__name__]

    # Config-Werte laden
    _excl = config_db.EXCLUDED_HSZ_SQL
    _offene_hs = config_db.OFFENE_HOCHSCHULE_SQL
    _sg_stamm_1 = config_db.get_param("stammdaten", "statusgruppe", _SG_BEGINNER)
    _sg_stamm_2 = config_db.get_param("stammdaten", "statusgruppe_2", _SG_QUEREINSTEIGER)
    _sg_zuz = config_db.get_param("zuzahler", "statusgruppe", _SG_GESAMTSTUDIERENDE)
    _sg_anr_1 = config_db.get_param("anrechnungen", "statusgruppe_1", _SG_BEGINNER)
    _sg_anr_2 = config_db.get_param("anrechnungen", "statusgruppe_2", _SG_QUEREINSTEIGER)
    _jahre_stamm = str(config_db.get_param_int("stammdaten", "jahre_zurueck", 2))
    _kohorten_j = str(config_db.get_param_int("studienerfolg", "kohorten_jahre", 5))
    _uebergang_j = str(config_db.get_param_int("uebergang", "kohorten_jahre", 5))
    _herkunft_j = str(config_db.get_param_int("herkunft", "kohorten_jahre", 5))
    _jahre_zuz = str(config_db.get_param_int("zuzahler", "jahre_zurueck", 4))
    _vertiefung_von = config_db.get_param("vertiefung", "datum_von", "2018-09-01")
    _vertiefung_bis = config_db.get_param("vertiefung", "datum_bis", "2021-09-01")
    _hz_von = config_db.get_param("hochschulzertifikate", "datum_von", "2021-08-01")
    _ue_raumids = config_db.get_filter_sql("UE_RAUMID")
    _ue_veransttyp = config_db.get_filter_sql("UE_VERANSTTYP")
    _ue_produktgruppe = config_db.get_filter_sql("UE_PRODUKTGRUPPE")
    _ue_statusrpl = config_db.get_filter_sql("UE_STATUSRPL")
    _vertiefung_art = config_db.get_filter_sql("VERTIEFUNG_ART")
    _vertiefung_fach_excl = config_db.get_filter_sql("VERTIEFUNG_FACH")
    _leistungsart_ignore = config_db.get_filter_sql("LEISTUNGSART_IGNORE")
    _zuzahler_empf = config_db.get_filter_sql("ZUZAHLER_EMPF")
    _zuzahler_kostentyp = (
        config_db.get_filter_values("ZUZAHLER_KOSTENTYP")[0]
        if config_db.get_filter_values("ZUZAHLER_KOSTENTYP")
        else "Arbeitgeber"
    )
    _dual_format = config_db.get_filter_sql("DUAL_STUDIENFORMAT")
    _dual_bildung = (
        config_db.get_filter_values("DUAL_BILDUNGSABSCHNITT")[0]
        if config_db.get_filter_values("DUAL_BILDUNGSABSCHNITT")
        else "Erstausbildung"
    )

    # Definiere Ersetzungsregeln: (altes_pattern, neues_pattern)
    replacements = [
        # Excluded Hochschulzentren
        ("'Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg'", _excl),
        # Ausrichtung OBS
        (
            "ISNULL(s.Ausrichtung, '') <> 'OBS'",
            "s.Ausrichtung = 'national'",
        ),
        # StatusGruppe Stammdaten (Beginner + Quereinsteiger)
        (
            "sg.StatusGruppe IN ('Beginner mit UV', 'Quereinsteiger mit UV')",
            f"sg.StatusGruppe IN ('{_sg_stamm_1}', '{_sg_stamm_2}')",
        ),
        # StatusGruppe Anrechnungen
        (
            "sg.StatusGruppe IN ('Beginner mit UV', 'Quereinsteiger mit UV')",
            f"sg.StatusGruppe IN ('{_sg_anr_1}', '{_sg_anr_2}')",
        ),
        # Offene Hochschule
        (
            "AnrechnungsGrund IN ('andere BW/IBW', 'andere Fortbildungen', 'eigene BW/IBW', 'eigene Ök', 'Fachkaufleute', 'IHK-Betriebswirt', 'IHK-Fachwirt')",
            f"AnrechnungsGrund IN ({_offene_hs})",
        ),
        # Vertiefung: Container-Arten
        (
            "mc.Art IN ('Vertiefungsrichtung', 'Wahlpflichtmodul', 'Wahlmodul')",
            f"mc.Art IN ({_vertiefung_art})",
        ),
        # Vertiefung: Fachgebiete exclude
        (
            "fg.Fachgebiet NOT IN ('General Studies Wahlmodul ZEUGNISSE', N'Zusatzwahlfächer')",
            f"fg.Fachgebiet NOT IN ({_vertiefung_fach_excl})",
        ),
        # Vertiefung: Datum
        (">= '2018-09-01'", f">= '{_vertiefung_von}'"),
        ("< '2021-09-01'", f"< '{_vertiefung_bis}'"),
        # Hochschulzertifikate Datum
        (">= '2021-08-01'", f">= '{_hz_von}'"),
        # UE: Raum-IDs
        ("r.RaumID NOT IN (274,285,349,845,1608)", f"r.RaumID NOT IN ({_ue_raumids})"),
        # UE: Veranstaltungstypen
        (
            "b.Veranstaltungstyp NOT IN ('Sonderveranstaltung')",
            f"b.Veranstaltungstyp NOT IN ({_ue_veransttyp})",
        ),
        # UE: Produktgruppen
        (
            "l.Produktgruppe IN ('Studium','Akademische Weiterbildung')",
            f"l.Produktgruppe IN ({_ue_produktgruppe})",
        ),
        # UE: StatusRPL
        ("l.StatusRPL IN ('A','P')", f"l.StatusRPL IN ({_ue_statusrpl})"),
        # Leistungsarten ignorieren
        (
            "la.LeistungsArtAnzeigeName NOT IN ('Einschreibehindernispruefung', 'Kooperation')",
            f"la.LeistungsArtAnzeigeName NOT IN ({_leistungsart_ignore})",
        ),
        # Zuzahler: Rechnungsempfänger
        (
            "LTRIM(RTRIM(r.RechEmpfaenger)) NOT IN ('Mitarbeiter')",
            f"LTRIM(RTRIM(r.RechEmpfaenger)) NOT IN ({_zuzahler_empf})",
        ),
        # Zuzahler: KostenÜbernahme
        (
            "ztn.KostenUebernahmeDurch = 'Arbeitgeber'",
            f"ztn.KostenUebernahmeDurch = '{_zuzahler_kostentyp}'",
        ),
        # Dual-Studierende: Studienformat
        (
            "holy.Studienformat IN ('ausbildungsintegrierend', 'berufsintegrierend', 'berufsbegleitend +')",
            f"holy.Studienformat IN ({_dual_format})",
        ),
        # Dual-Studierende: Bildungsabschnitt
        (
            "holy.Bildungsabschnitt = 'Erstausbildung'",
            f"holy.Bildungsabschnitt = '{_dual_bildung}'",
        ),
    ]

    # Zeitraum-Parameter (müssen vorsichtig ersetzt werden)
    zeit_replacements = [
        ("YEAR(GETDATE())-2", f"YEAR(GETDATE())-{_jahre_stamm}"),
        ("YEAR(GETDATE()) - 2", f"YEAR(GETDATE()) - {_jahre_stamm}"),
        (
            "YEAR(DATEADD(YEAR, -5, GETDATE()))",
            f"YEAR(DATEADD(YEAR, -{_kohorten_j}, GETDATE()))",
        ),
        ("YEAR(GETDATE()) - 4", f"YEAR(GETDATE()) - {_jahre_zuz}"),
    ]

    # Alle SQL-Variablen im Modul patchen
    sql_vars = [
        name for name in dir(module) if name.startswith("SQL_") or name.startswith("_ZUZAHLER")
    ]
    for var_name in sql_vars:
        val = getattr(module, var_name)
        if not isinstance(val, str):
            continue
        for old, new in replacements:
            val = val.replace(old, new)
        for old, new in zeit_replacements:
            val = val.replace(old, new)
        setattr(module, var_name, val)

    print("[Queries] SQL-Strings mit DB-Konfiguration gepatcht")


# ─── Queries initialisieren ───
_build_sql_queries()
_patch_remaining_queries()


# ═══════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════


def init_queries():
    """Initialisiert alle SQL-Queries. Wird beim App-Start und bei Config-Reload aufgerufen."""
    _build_sql_queries()
    _patch_remaining_queries()
