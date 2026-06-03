import pyodbc

conn = pyodbc.connect(
    "DRIVER={SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes"
)
cur = conn.cursor()

# Suche nach der Quelle der Excel-Daten (studiengang_tn_ID)
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME 
    FROM BCW_DWH.INFORMATION_SCHEMA.COLUMNS 
    WHERE COLUMN_NAME LIKE '%studiengang_tn%'
    ORDER BY TABLE_NAME
""")
print("Tabellen mit studiengang_tn_ID:")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}.{row[2]}")

print()

# Suche nach AnzahlVerlängerungsSem
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME 
    FROM BCW_DWH.INFORMATION_SCHEMA.COLUMNS 
    WHERE COLUMN_NAME LIKE '%Verlaengerung%' OR COLUMN_NAME LIKE '%Verlängerung%'
    ORDER BY TABLE_NAME
""")
print("Tabellen mit Verlaengerung-Spalten:")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}.{row[2]}")

print()

# Auch in BCW_STA suchen
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME 
    FROM BCW_STA.INFORMATION_SCHEMA.COLUMNS 
    WHERE COLUMN_NAME LIKE '%Cluster_Status%' OR COLUMN_NAME LIKE '%studiengang_tn%'
    ORDER BY TABLE_NAME
""")
print("BCW_STA Tabellen mit Cluster/tn_ID:")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}.{row[2]}")

print()

# Vergleich RSZ vs AnzahlVerlängerungsSem: gleiche Ergebnisse?
# Prüfe C_StudienEin_ausstieg für BBA: wie viele haben RSZ=1 (= in Verlängerung)?
cur.execute("""
    SELECT 
        RegelstudienzeitAbgeschlossen, AusstiegsCluster, COUNT(*) AS Anzahl
    FROM BCW_DWH.dwh.C_StudienEin_ausstieg
    WHERE Institut = 'FOM' AND Produktkuerzel = 'BBA'
      AND Kohorte >= '2021-WS' AND Kohorte <= '2026-SS'
      AND Gueltige_Codierung = 1
      AND AusstiegsCluster = 'Eingeschrieben'
    GROUP BY RegelstudienzeitAbgeschlossen, AusstiegsCluster
""")
print("C_StudienEin_ausstieg BBA Eingeschriebene nach RSZ:")
for row in cur.fetchall():
    rsz_label = "Verlaengerung" if row[0] == 1 else "regulaer"
    print(f"  RSZ={row[0]} ({rsz_label}): {row[2]}")

conn.close()
