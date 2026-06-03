import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes')
cur = conn.cursor()

# Test with Holy-aligned WHERE clause
cur.execute("""
    WITH LatestStatus AS (
        SELECT sjs.StudienEintragFID, sjs.Status, sjs.Zustand, sjs.Fachsemester,
            se.Exmatrikulationsgrund, cea.Ausstiegsstatus, l.Produktkuerzel, l.Kohorte,
            ROW_NUMBER() OVER (PARTITION BY sjs.StudienEintragFID ORDER BY sem.SemesterStart DESC) as rn
        FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
        JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
        JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
        JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
        JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
        LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg cea ON cea.StudienEintragID = se.StudienEintragID
        WHERE sem.SemesterStart < GETDATE()
          AND l.Institut = 'FOM' AND p.Testperson = 0
          AND se.ImmatrikulationsDatum <= GETDATE()
          AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
          AND LEFT(sjs.Status, 2) <> 'VT'
          AND (cea.Ausstiegsstatus NOT IN ('-', 'V', 'US')
               OR sjs.Zustand = '1' AND cea.Ausstiegsstatus IN ('-', 'V', 'US'))
          AND sjs.Status NOT IN ('Vorkurs','Urlaubssemester')
          AND l.Produktkuerzel = 'BBA'
          AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
          AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
          AND l.Kohorte <= CONCAT(CAST(YEAR(GETDATE()) AS VARCHAR), CASE WHEN MONTH(GETDATE()) >= 9 THEN '-WS' ELSE '-SS' END)
    )
    SELECT
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
        END AS AusstiegsCluster,
        CASE WHEN Ausstiegsstatus = 'V' THEN 1 ELSE 0 END AS RSZ,
        COUNT(*) AS Cnt
    FROM LatestStatus
    WHERE rn = 1
    GROUP BY
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
        END,
        CASE WHEN Ausstiegsstatus = 'V' THEN 1 ELSE 0 END
    ORDER BY AusstiegsCluster, RSZ
""")

print("=== Holy-aligned CTE (BBA, 5-Jahres-Kohorte) ===")
total = 0
clusters = {}
for row in cur.fetchall():
    cluster = row[0] if row[0] else 'NULL'
    rsz = row[1]
    cnt = row[2]
    total += cnt
    key = f"{cluster}(RSZ={rsz})"
    clusters[key] = cnt
    print(f"  {key:30s}  {cnt:6d}")

denom = total - clusters.get('NULL(RSZ=0)', 0)
reg = clusters.get('Eingeschrieben(RSZ=0)', 0)
verl = clusters.get('Eingeschrieben(RSZ=1)', 0)
print(f"\n  TOTAL: {total}")
print(f"  Denominator (excl NULL): {denom}")
print(f"  regulär:      {reg:6d}  ({100*reg/denom:.1f}%)")
print(f"  Verlängerung: {verl:6d}  ({100*verl/denom:.1f}%)")
print(f"  Abbrecher:    {clusters.get('Abbrecher(RSZ=0)',0):6d}  ({100*clusters.get('Abbrecher(RSZ=0)',0)/denom:.1f}%)")
print(f"  Absolvent:    {clusters.get('Absolvent(RSZ=0)',0):6d}  ({100*clusters.get('Absolvent(RSZ=0)',0)/denom:.1f}%)")
print(f"  Wechsler:     {clusters.get('Wechsler(RSZ=0)',0):6d}  ({100*clusters.get('Wechsler(RSZ=0)',0)/denom:.1f}%)")

conn.close()
