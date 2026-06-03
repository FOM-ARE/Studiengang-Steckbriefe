"""Check why app shows 47.9% aktiv-regulär vs user's 49.4%."""
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()

sql = """
WITH LatestStatus AS (
    SELECT
        sjs.StudienEintragFID, sjs.Status, sjs.Zustand, sjs.Fachsemester,
        se.ExmatrikulationsDatum, se.ImmatrikulationsDatum, se.Exmatrikulationsgrund,
        l.Produktkuerzel, l.Kohorte, l.LehrgangsEnde, l.Hochschulzentrum,
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
      AND sjs.Status NOT IN ('Vorkurs','nicht begonnen','Statistik nein',
                             'OnlineAnmeldung','Urlaubssemester',
                             'unter Vorbehalt',
                             'Anrechnung Quereinsteiger extern unter Vorbehalt',
                             'Anrechnung Quereinsteiger intern unter Vorbehalt',
                             'Quereinsteiger extern unter Vorbehalt',
                             'Quereinsteiger intern unter Vorbehalt')
      AND l.Produktkuerzel NOT IN ('WBS','GBA')
      AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
      AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-10,GETDATE())) AS VARCHAR),'-WS')
)
SELECT
    Status,
    Exmatrikulationsgrund,
    CASE
        WHEN Status LIKE '%Kooperationsweiterleitung%' THEN 'NULL_Koop'
        WHEN Status LIKE '%Abbrecher%' AND Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN 'NULL_Auslauf'
        WHEN Status LIKE '%Abbrecher%' THEN 'Abbrecher'
        WHEN Status = 'Ausgeschieden' THEN 'Abbrecher'
        WHEN Status = 'fehlende R' + CHAR(252) + 'ckmeldung' THEN 'Abbrecher'
        WHEN Status LIKE '%Absolvent%' THEN 'Absolvent'
        WHEN Status LIKE '%Wechsel%' THEN 'Wechsler'
        WHEN Zustand = '1' AND Status IN ('Verl' + CHAR(228) + 'ngerer','Wechsler/Verl' + CHAR(228) + 'ngerer') THEN 'Eingeschrieben_V'
        WHEN Zustand = '1' AND Status IN ('R' + CHAR(252) + 'ckmeldung','Beginner','QuerBeginner',
            'Quereinsteiger extern','Quereinsteiger intern','Wechsler',
            'Wechsler unter Vorbehalt',CHAR(220) + 'bernahme','Anrechnung','Erasmus',
            'Stipendium') THEN 'Eingeschrieben_R'
        ELSE 'NULL_Else'
    END AS Cluster,
    COUNT(*) AS Anzahl
FROM LatestStatus
WHERE rn = 1 AND Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
  AND Kohorte >= '2021-WS'
  AND Kohorte <= '2026-SS'
GROUP BY Status, Exmatrikulationsgrund,
    CASE
        WHEN Status LIKE '%Kooperationsweiterleitung%' THEN 'NULL_Koop'
        WHEN Status LIKE '%Abbrecher%' AND Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN 'NULL_Auslauf'
        WHEN Status LIKE '%Abbrecher%' THEN 'Abbrecher'
        WHEN Status = 'Ausgeschieden' THEN 'Abbrecher'
        WHEN Status = 'fehlende R' + CHAR(252) + 'ckmeldung' THEN 'Abbrecher'
        WHEN Status LIKE '%Absolvent%' THEN 'Absolvent'
        WHEN Status LIKE '%Wechsel%' THEN 'Wechsler'
        WHEN Zustand = '1' AND Status IN ('Verl' + CHAR(228) + 'ngerer','Wechsler/Verl' + CHAR(228) + 'ngerer') THEN 'Eingeschrieben_V'
        WHEN Zustand = '1' AND Status IN ('R' + CHAR(252) + 'ckmeldung','Beginner','QuerBeginner',
            'Quereinsteiger extern','Quereinsteiger intern','Wechsler',
            'Wechsler unter Vorbehalt',CHAR(220) + 'bernahme','Anrechnung','Erasmus',
            'Stipendium') THEN 'Eingeschrieben_R'
        ELSE 'NULL_Else'
    END
ORDER BY Cluster, Anzahl DESC
"""

cursor.execute(sql)
rows = cursor.fetchall()

# Zusammenfassung
totals = {}
for r in rows:
    cluster = r[2]
    cnt = r[3]
    totals[cluster] = totals.get(cluster, 0) + cnt

gesamt_mit_null = sum(totals.values())
gesamt_ohne_null = sum(v for k, v in totals.items() if not k.startswith('NULL'))

print(f"Gesamt (inkl. NULL): {gesamt_mit_null}")
print(f"Gesamt (ohne NULL = App-Denominator): {gesamt_ohne_null}")
print()

for cluster in sorted(totals.keys()):
    cnt = totals[cluster]
    pct_mit = round(cnt / gesamt_mit_null * 100, 1)
    pct_ohne = round(cnt / gesamt_ohne_null * 100, 1) if not cluster.startswith('NULL') else '-'
    print(f"  {cluster:20s}: {cnt:5d}  ({pct_mit}% von Gesamt | {pct_ohne}% ohne NULL)")

print(f"\n--- NULL-Details ---")
for r in rows:
    if r[2].startswith('NULL'):
        print(f"  Status='{r[0]}', Exmatgrund='{r[1]}', Cluster={r[2]}, Anzahl={r[3]}")

conn.close()
