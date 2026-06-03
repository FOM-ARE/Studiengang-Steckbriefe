import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# 1. StudierendenstatusJeSemester - Spalten
print("=== StudierendenstatusJeSemester ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME LIKE '%StudierendenstatusJeSemester%'
    OR TABLE_NAME LIKE '%Studierendenstatus%Semester%'
    ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  {r[0]} ({r[1]})")
else:
    print("  NICHT GEFUNDEN - suche ähnliche...")
    cur.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME LIKE '%Studierenden%'
        OR TABLE_NAME LIKE '%status%Sem%'
        ORDER BY TABLE_NAME
    """)
    for r in cur.fetchall():
        print(f"  {r[0]}.{r[1]}")

print()

# 2. StudienEintraege - Spalten
print("=== StudienEintraege ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'StudienEintraege'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()

# 3. StudierendenInformationen
print("=== StudierendenInformationen ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME LIKE '%StudierendenInformation%'
    ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  {r[0]} ({r[1]})")
else:
    print("  NICHT GEFUNDEN - suche ähnliche...")
    cur.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME LIKE '%Studierend%Info%'
        OR TABLE_NAME LIKE '%PersonenInfo%'
        OR TABLE_NAME LIKE '%Personen%'
        ORDER BY TABLE_NAME
    """)
    for r in cur.fetchall():
        print(f"  {r[0]}.{r[1]}")

conn.close()
