import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes"
)
cur = conn.cursor()

# Check 1: Are there duplicate StudienEintragIDs in C_StudienEin_ausstieg?
print("=== Duplikate in C_StudienEin_ausstieg? ===")
cur.execute("""
    SELECT StudienEintragID, COUNT(*) as cnt
    FROM BCW_DWH.dwh.C_StudienEin_ausstieg
    GROUP BY StudienEintragID
    HAVING COUNT(*) > 1
""")
dups = cur.fetchall()
print(f"  Einträge mit Duplikaten: {len(dups)}")
if dups:
    for row in dups[:5]:
        print(f"    StudienEintragID={row[0]}, Count={row[1]}")

# Check 2: Total count WITHOUT cea JOIN
print("\n=== Total OHNE C_StudienEin_ausstieg JOIN ===")
cur.execute("""
    WITH LatestStatus AS (
        SELECT
            sjs.StudienEintragFID,
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
          AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
    )
    SELECT COUNT(*) FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = 'BBA'
      AND Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
      AND Kohorte <= CONCAT(CAST(YEAR(GETDATE()) AS VARCHAR), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
""")
# Oops - we're not selecting Produktkuerzel/Kohorte in this simple query
# Let me fix by including those fields
cur.execute("""
    WITH LatestStatus AS (
        SELECT
            sjs.StudienEintragFID,
            l.Produktkuerzel,
            l.Kohorte,
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
          AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
    )
    SELECT COUNT(*) FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = 'BBA'
      AND Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
      AND Kohorte <= CONCAT(CAST(YEAR(GETDATE()) AS VARCHAR), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
""")
row = cur.fetchone()
print(f"  Total ohne cea JOIN: {row[0]}")

# Check 3: Total count WITH cea JOIN
print("\n=== Total MIT C_StudienEin_ausstieg LEFT JOIN ===")
cur.execute("""
    WITH LatestStatus AS (
        SELECT
            sjs.StudienEintragFID,
            l.Produktkuerzel,
            l.Kohorte,
            ROW_NUMBER() OVER (PARTITION BY sjs.StudienEintragFID ORDER BY sem.SemesterStart DESC) as rn
        FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
        JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
        JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
        JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
        JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
        LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg cea ON cea.StudienEintragID = se.StudienEintragID
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
          AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
    )
    SELECT COUNT(*) FROM LatestStatus
    WHERE rn = 1 AND Produktkuerzel = 'BBA'
      AND Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
      AND Kohorte <= CONCAT(CAST(YEAR(GETDATE()) AS VARCHAR), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
""")
row = cur.fetchone()
print(f"  Total mit cea JOIN:  {row[0]}")

conn.close()
