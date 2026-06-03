import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# 1. Personen: Geschlecht und Staatsangehoerigkeit im DWH vorhanden?
print("=== dwh.Personen - Geschlecht (sample) ===")
cur.execute("SELECT DISTINCT TOP 10 Geschlecht FROM BCW_DWH.dwh.Personen")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()
print("=== dwh.Personen - Staatsangehoerigkeit vorhanden? ===")
cur.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='dwh' AND TABLE_NAME='Personen' 
    AND COLUMN_NAME LIKE '%staat%'
""")
for r in cur.fetchall():
    print(f"  {r[0]}")

print()
print("=== dwh.Lehrgaenge - ZeitmodellDetail (sample) ===")
cur.execute(
    "SELECT DISTINCT TOP 10 ZeitmodellDetail FROM BCW_DWH.dwh.Lehrgaenge WHERE Institut='FOM'"
)
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()
print("=== dwh.Lehrgaenge - DualerStudiengang (sample) ===")
cur.execute("SELECT DISTINCT DualerStudiengang FROM BCW_DWH.dwh.Lehrgaenge WHERE Institut='FOM'")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()
print("=== dwh.Lehrgaenge - Ausrichtung (sample) ===")
cur.execute("SELECT DISTINCT TOP 15 Ausrichtung FROM BCW_DWH.dwh.Lehrgaenge WHERE Institut='FOM'")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()
print("=== dwh.Lehrgaenge - Lernform (sample) ===")
cur.execute("SELECT DISTINCT TOP 10 Lernform FROM BCW_DWH.dwh.Lehrgaenge WHERE Institut='FOM'")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()
print("=== dwh.Lehrgaenge - Produktart (sample) ===")
cur.execute("SELECT DISTINCT Top 10 Produktart FROM BCW_DWH.dwh.Lehrgaenge WHERE Institut='FOM'")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# Suche nach Bildungsabschnitt / Studienformat im DWH
print("=== Suche 'Bildungsabschnitt' / 'Studienformat' in DWH ===")
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE COLUMN_NAME LIKE '%Bildungs%' OR COLUMN_NAME LIKE '%Studienformat%'
    OR COLUMN_NAME LIKE '%bildung%' OR COLUMN_NAME LIKE '%format%'
""")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}.{r[2]}")

print()

# StatusGruppen table
print("=== dwh.StatusGruppen (Spalten) ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='dwh' AND TABLE_NAME='StatusGruppen'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()
print("=== StatusGruppen mit 'Beginner' (sample) ===")
cur.execute("""
    SELECT DISTINCT TOP 10 StatusGruppe, Status 
    FROM BCW_DWH.dwh.StatusGruppen 
    WHERE StatusGruppe LIKE '%Beginner%'
""")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]}")

conn.close()
