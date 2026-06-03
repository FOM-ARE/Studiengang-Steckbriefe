import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes')
cur = conn.cursor()

# Direkt C_StudienEin_ausstieg mit Holy-Filtern (OHNE SJS-CTE)
print("=== C_StudienEin_ausstieg DIREKT mit Holy-Filtern (BBA, 2021-WS bis 2026-SS) ===")
cur.execute("""
    SELECT
        CASE
            WHEN cea.Ausstiegsstatus = 'KoopWG' THEN NULL
            WHEN cea.Ausstiegsstatus = 'K' AND se.Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN NULL
            WHEN cea.Ausstiegsstatus = 'K' THEN 'Abbrecher'
            WHEN cea.Ausstiegsstatus IN ('WE', 'WPO', 'WSGO', 'WUS') THEN 'Wechsler'
            WHEN cea.Ausstiegsstatus = 'A' THEN 'Absolvent'
            WHEN cea.Ausstiegsstatus = 'US' THEN NULL
            WHEN cea.Ausstiegsstatus = 'V' THEN 'Eingeschrieben'
            WHEN cea.Ausstiegsstatus = '-' THEN 'Eingeschrieben'
            ELSE NULL
        END AS Cluster,
        CASE WHEN cea.Ausstiegsstatus = 'V' THEN 1 ELSE 0 END AS RSZ,
        COUNT(*) AS Cnt
    FROM BCW_DWH.dwh.C_StudienEin_ausstieg cea
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = cea.StudienEintragID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
    WHERE l.Produktkuerzel = 'BBA'
      AND l.Institut = 'FOM'
      AND p.Testperson = 0
      AND se.ImmatrikulationsDatum <= GETDATE()
      AND se.ImmatrikulationsDatum < se.ExmatrikulationsDatum
      AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
      AND l.Kohorte >= '2021-WS'
      AND l.Kohorte <= '2026-SS'
    GROUP BY
        CASE
            WHEN cea.Ausstiegsstatus = 'KoopWG' THEN NULL
            WHEN cea.Ausstiegsstatus = 'K' AND se.Exmatrikulationsgrund LIKE '0[_]Auslauf Kooperation%' THEN NULL
            WHEN cea.Ausstiegsstatus = 'K' THEN 'Abbrecher'
            WHEN cea.Ausstiegsstatus IN ('WE', 'WPO', 'WSGO', 'WUS') THEN 'Wechsler'
            WHEN cea.Ausstiegsstatus = 'A' THEN 'Absolvent'
            WHEN cea.Ausstiegsstatus = 'US' THEN NULL
            WHEN cea.Ausstiegsstatus = 'V' THEN 'Eingeschrieben'
            WHEN cea.Ausstiegsstatus = '-' THEN 'Eingeschrieben'
            ELSE NULL
        END,
        CASE WHEN cea.Ausstiegsstatus = 'V' THEN 1 ELSE 0 END
    ORDER BY Cluster, RSZ
""")

total = 0
null_total = 0
clusters = {}
for row in cur.fetchall():
    cluster = row[0] if row[0] else 'NULL'
    rsz = row[1]
    cnt = row[2]
    total += cnt
    if cluster == 'NULL':
        null_total += cnt
    key = f"{cluster}(RSZ={rsz})"
    clusters[key] = cnt
    print(f"  {key:30s}  {cnt:6d}")

denom = total - null_total
reg = clusters.get('Eingeschrieben(RSZ=0)', 0)
verl = clusters.get('Eingeschrieben(RSZ=1)', 0)
print(f"\n  TOTAL: {total}  (davon NULL/excluded: {null_total})")
print(f"  Denominator: {denom}")
print(f"  regulär:      {reg:6d}  ({100*reg/denom:.1f}%)")
print(f"  Verlängerung: {verl:6d}  ({100*verl/denom:.1f}%)")
print(f"  Abbrecher:    {clusters.get('Abbrecher(RSZ=0)',0):6d}  ({100*clusters.get('Abbrecher(RSZ=0)',0)/denom:.1f}%)")
print(f"  Absolvent:    {clusters.get('Absolvent(RSZ=0)',0):6d}  ({100*clusters.get('Absolvent(RSZ=0)',0)/denom:.1f}%)")
print(f"  Wechsler:     {clusters.get('Wechsler(RSZ=0)',0):6d}  ({100*clusters.get('Wechsler(RSZ=0)',0)/denom:.1f}%)")

# Auch: Zustand-Check - wie viele haben Zustand != 1 (aus SJS)?
print("\n=== Vergleich: SJS-CTE Ansatz (Holy-aligned) ===")
cur.execute("""
    WITH LatestStatus AS (
        SELECT sjs.StudienEintragFID, cea.Ausstiegsstatus, se.Exmatrikulationsgrund,
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
          AND (cea.Ausstiegsstatus NOT IN ('-', 'V', 'US') OR sjs.Zustand = '1')
          AND sjs.Status NOT IN ('Vorkurs','Urlaubssemester')
          AND l.Produktkuerzel = 'BBA'
          AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
          AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
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
        END AS Cluster,
        COUNT(*) AS Cnt
    FROM LatestStatus WHERE rn = 1
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
        END
    ORDER BY Cluster
""")
total2 = 0
null2 = 0
for row in cur.fetchall():
    c = row[0] if row[0] else 'NULL'
    total2 += row[1]
    if c == 'NULL': null2 += row[1]
    print(f"  {c:15s}  {row[1]:6d}")
print(f"  SJS-Total: {total2}, Denom: {total2-null2}")

# Differenz: welche StudienEintraege sind in cea aber nicht in SJS-CTE?
print(f"\n  Differenz cea-direkt vs SJS: {denom} vs {total2-null2} = {denom - (total2-null2)} mehr in cea")

conn.close()
