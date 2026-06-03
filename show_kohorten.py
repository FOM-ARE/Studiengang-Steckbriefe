import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes;"
)
cur = conn.cursor()

cur.execute("""
SELECT CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS') AS untere_grenze,
       CASE WHEN MONTH(GETDATE()) BETWEEN 4 AND 9 THEN CONCAT(CAST(YEAR(GETDATE())-1 AS VARCHAR),'-SS')
            WHEN MONTH(GETDATE()) >= 10 THEN CONCAT(CAST(YEAR(GETDATE())-1 AS VARCHAR),'-WS')
            ELSE CONCAT(CAST(YEAR(GETDATE())-2 AS VARCHAR),'-WS') END AS obere_grenze
""")
r = cur.fetchone()
print(f"Kohortenfilter: >= {r[0]} AND <= {r[1]}")
print()
print("Enthaltene Kohorten (BBA):")
cur.execute("""
SELECT DISTINCT l.Kohorte
FROM BCW_DWH.dwh.Lehrgaenge l
WHERE l.Institut = 'FOM' AND l.Produktkuerzel = 'BBA'
  AND l.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR,-5,GETDATE())) AS VARCHAR),'-WS')
  AND l.Kohorte <= CASE WHEN MONTH(GETDATE()) BETWEEN 4 AND 9 THEN CONCAT(CAST(YEAR(GETDATE())-1 AS VARCHAR),'-SS')
                        WHEN MONTH(GETDATE()) >= 10 THEN CONCAT(CAST(YEAR(GETDATE())-1 AS VARCHAR),'-WS')
                        ELSE CONCAT(CAST(YEAR(GETDATE())-2 AS VARCHAR),'-WS') END
ORDER BY l.Kohorte
""")
for r in cur.fetchall():
    print(f"  {r[0]}")
conn.close()
