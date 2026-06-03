"""
Rewrite der MySQL-View V_Bw_Studienausstieg fuer das DWH (SQL Server).
Verwendet: StudierendenstatusJeSemester, StudienEintraege, Lehrgaenge, Personen, Semester
Ziel: Studienerfolg-Berechnung mit gleicher Logik wie Holy-View.
"""

import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# Der neue Query: basierend auf StudierendenstatusJeSemester statt C_StudienEin_ausstieg
SQL_STUDIENERFOLG_NEW = """
WITH LatestStatus AS (
    SELECT 
        sjs.StudienEintragFID,
        sjs.Status,
        sjs.Zustand,
        sjs.Fachsemester,
        se.ExmatrikulationsDatum,
        se.ImmatrikulationsDatum,
        se.Exmatrikulationsgrund,
        l.Produktkuerzel,
        l.Kohorte,
        l.LehrgangsEnde,
        l.Hochschulzentrum,
        l.Institut,
        sem.SemesterStart,
        sem.SemesterKuerzel,
        ROW_NUMBER() OVER (PARTITION BY sjs.StudienEintragFID ORDER BY sem.SemesterStart DESC) as rn
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
    JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
    WHERE sjs.Zustand = '1'
      AND sem.SemesterStart < GETDATE()
      AND l.Institut = 'FOM'
      AND p.Testperson = 0
      AND se.ImmatrikulationsDatum <= GETDATE()
      AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
      AND sjs.Status NOT IN ('Vorkurs', 'nicht begonnen', 'Statistik nein', 
                             'OnlineAnmeldung', 'Urlaubssemester',
                             'unter Vorbehalt', 'Anrechnung Quereinsteiger extern unter Vorbehalt',
                             'Anrechnung Quereinsteiger intern unter Vorbehalt',
                             'Quereinsteiger extern unter Vorbehalt',
                             'Quereinsteiger intern unter Vorbehalt')
      AND l.Produktkuerzel NOT IN ('WBS', 'GBA')
      AND l.Hochschulzentrum NOT IN ('Venlo', 'Sofia', 'Bangalore', 'Pune')
      AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -10, GETDATE())) AS VARCHAR), '-WS')
)
SELECT 
    CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END AS Fachsem,
    CASE 
        -- Kooperationsweiterleitung -> ausschliessen
        WHEN Status LIKE '%Kooperationsweiterleitung%' THEN NULL
        WHEN Status LIKE '%Abbrecher%' AND Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN NULL
        -- Abbrecher
        WHEN Status LIKE '%Abbrecher%' THEN 'Abbrecher'
        WHEN Status = 'Ausgeschieden' THEN 'Abbrecher'
        WHEN Status = 'fehlende Rückmeldung' THEN 'Abbrecher'
        -- Absolvent
        WHEN Status LIKE '%Absolvent%' THEN 'Absolvent'
        -- Wechsler (alle Wechsel-Varianten)
        WHEN Status LIKE '%Wechsel%' THEN 'Wechsler'
        -- Eingeschrieben in Verlaengerung
        WHEN Zustand = '1' AND Status IN ('Verlängerer', 'Wechsler/Verlängerer') THEN 'Eingeschrieben'
        -- Regulaer eingeschrieben
        WHEN Zustand = '1' AND Status IN ('Rückmeldung', 'Beginner', 'QuerBeginner',
            'Quereinsteiger extern', 'Quereinsteiger intern', 'Wechsler', 
            'Wechsler unter Vorbehalt', 'Übernahme', 'Anrechnung', 'Erasmus',
            'Stipendium') THEN 'Eingeschrieben'
        ELSE NULL
    END AS AusstiegsCluster,
    CASE 
        WHEN Zustand = '1' AND Status IN ('Verlängerer', 'Wechsler/Verlängerer') THEN 1
        ELSE 0
    END AS RSZ,
    COUNT(*) AS Anzahl
FROM LatestStatus
WHERE rn = 1
  AND Produktkuerzel = 'BBA'
  AND Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -5, GETDATE())) AS VARCHAR), '-WS')
  AND Kohorte <= '2025-SS'
GROUP BY 
    CASE WHEN Fachsemester > 8 THEN '9+' ELSE CAST(Fachsemester AS VARCHAR) END,
    CASE 
        WHEN Status LIKE '%Kooperationsweiterleitung%' THEN NULL
        WHEN Status LIKE '%Abbrecher%' AND Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN NULL
        WHEN Status LIKE '%Abbrecher%' THEN 'Abbrecher'
        WHEN Status = 'Ausgeschieden' THEN 'Abbrecher'
        WHEN Status = 'fehlende Rückmeldung' THEN 'Abbrecher'
        WHEN Status LIKE '%Absolvent%' THEN 'Absolvent'
        WHEN Status LIKE '%Wechsel%' THEN 'Wechsler'
        WHEN Zustand = '1' AND Status IN ('Verlängerer', 'Wechsler/Verlängerer') THEN 'Eingeschrieben'
        WHEN Zustand = '1' AND Status IN ('Rückmeldung', 'Beginner', 'QuerBeginner',
            'Quereinsteiger extern', 'Quereinsteiger intern', 'Wechsler', 
            'Wechsler unter Vorbehalt', 'Übernahme', 'Anrechnung', 'Erasmus',
            'Stipendium') THEN 'Eingeschrieben'
        ELSE NULL
    END,
    CASE 
        WHEN Zustand = '1' AND Status IN ('Verlängerer', 'Wechsler/Verlängerer') THEN 1
        ELSE 0
    END
ORDER BY Fachsem
"""

print("Neuer Query (DWH-basiert, BBA, 2021-WS bis 2025-SS):")
print("=" * 70)
cur.execute(SQL_STUDIENERFOLG_NEW)
rows = cur.fetchall()

from collections import defaultdict

totals = defaultdict(int)
grand_total = 0

for r in rows:
    fachsem, cluster, rsz, anzahl = r
    if cluster is None:
        continue
    key = f"{cluster}_RSZ{rsz}" if cluster == "Eingeschrieben" else cluster
    totals[key] += anzahl
    grand_total += anzahl

print(f"\nGesamt: {grand_total}")
print("\nKategorie-Verteilung:")
for k in ["Eingeschrieben_RSZ0", "Eingeschrieben_RSZ1", "Abbrecher", "Absolvent", "Wechsler"]:
    v = totals.get(k, 0)
    pct = v / grand_total * 100 if grand_total > 0 else 0
    print(f"  {k:<30} {v:>6}  ({pct:.1f}%)")

print("\nVergleich mit altem Query (C_StudienEin_ausstieg, gleicher Filter):")
print(f"  {'Alt: Eingeschrieben RSZ=0':<30} {'3893':>6}  (39.2%)")
print(f"  {'Alt: Eingeschrieben RSZ=1':<30} {'1098':>6}  (11.1%)")
print(f"  {'Alt: Abbrecher':<30} {'1897':>6}")
print(f"  {'Alt: Absolvent':<30} {'1723':>6}")
print(f"  {'Alt: Wechsler':<30} {'1220':>6}")
print(f"  {'Alt: GESAMT':<30} {'9931':>6}")

# Check: NULL/excluded rows
print("\nAusgeschlossene (NULL-Cluster):")
cur.execute("""
WITH LatestStatus AS (
    SELECT 
        sjs.StudienEintragFID,
        sjs.Status,
        sjs.Zustand,
        sjs.Fachsemester,
        se.ExmatrikulationsDatum,
        se.ImmatrikulationsDatum,
        se.Exmatrikulationsgrund,
        l.Produktkuerzel,
        l.Kohorte,
        l.LehrgangsEnde,
        l.Hochschulzentrum,
        l.Institut,
        sem.SemesterStart,
        ROW_NUMBER() OVER (PARTITION BY sjs.StudienEintragFID ORDER BY sem.SemesterStart DESC) as rn
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
    JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
    WHERE sjs.Zustand = '1'
      AND sem.SemesterStart < GETDATE()
      AND l.Institut = 'FOM'
      AND p.Testperson = 0
      AND se.ImmatrikulationsDatum <= GETDATE()
      AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
      AND sjs.Status NOT IN ('Vorkurs', 'nicht begonnen', 'Statistik nein', 
                             'OnlineAnmeldung', 'Urlaubssemester',
                             'unter Vorbehalt', 'Anrechnung Quereinsteiger extern unter Vorbehalt',
                             'Anrechnung Quereinsteiger intern unter Vorbehalt',
                             'Quereinsteiger extern unter Vorbehalt',
                             'Quereinsteiger intern unter Vorbehalt')
      AND l.Produktkuerzel NOT IN ('WBS', 'GBA')
      AND l.Hochschulzentrum NOT IN ('Venlo', 'Sofia', 'Bangalore', 'Pune')
      AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -10, GETDATE())) AS VARCHAR), '-WS')
)
SELECT Status, COUNT(*) as cnt
FROM LatestStatus
WHERE rn = 1
  AND Produktkuerzel = 'BBA'
  AND Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -5, GETDATE())) AS VARCHAR), '-WS')
  AND Kohorte <= '2025-SS'
  AND CASE 
        WHEN Status LIKE '%Kooperationsweiterleitung%' THEN NULL
        WHEN Status LIKE '%Abbrecher%' AND Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN NULL
        WHEN Status LIKE '%Abbrecher%' THEN 'Abbrecher'
        WHEN Status = 'Ausgeschieden' THEN 'Abbrecher'
        WHEN Status = 'fehlende Rückmeldung' THEN 'Abbrecher'
        WHEN Status LIKE '%Absolvent%' THEN 'Absolvent'
        WHEN Status LIKE '%Wechsel%' THEN 'Wechsler'
        WHEN Zustand = '1' AND Status IN ('Verlängerer', 'Wechsler/Verlängerer') THEN 'Eingeschrieben'
        WHEN Zustand = '1' AND Status IN ('Rückmeldung', 'Beginner', 'QuerBeginner',
            'Quereinsteiger extern', 'Quereinsteiger intern', 'Wechsler', 
            'Wechsler unter Vorbehalt', 'Übernahme', 'Anrechnung', 'Erasmus',
            'Stipendium') THEN 'Eingeschrieben'
        ELSE NULL
    END IS NULL
GROUP BY Status
ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
