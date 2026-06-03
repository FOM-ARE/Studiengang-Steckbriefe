import pyodbc
conn = pyodbc.connect('DRIVER={SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes')
cur = conn.cursor()

# Spalten von C_Studierendenzahlen
cur.execute("SELECT TOP 1 * FROM BCW_DWH.dwh.C_Studierendenzahlen WHERE Produktkuerzel = 'BBA'")
cols = [d[0] for d in cur.description]
print(f'C_Studierendenzahlen Spalten ({len(cols)}):')
for c in cols:
    print(f'  {c}')

print()
print()

# Die Excel hat diese Spalten: Cluster_Statuskuerzel, Verlaengerungssem_Cluster, 
# Regelstudienzeit, AnzahlVerlängerungsSem, noch_eingeschrieben, Statuskuerzel
# Pruefen ob diese aus einer anderen Tabelle/View kommen
# Die Excel-Abfrage heisst "Abfrage" (Spalte 0) - vermutlich ein Power Query

# Suche nach Views die Cluster_Statuskuerzel enthalten
cur.execute("""
    SELECT TABLE_NAME, COLUMN_NAME 
    FROM BCW_DWH.INFORMATION_SCHEMA.COLUMNS 
    WHERE COLUMN_NAME LIKE '%Cluster%Status%'
       OR COLUMN_NAME LIKE '%Verlaengerungssem%'
       OR COLUMN_NAME LIKE '%AnzahlVerl%'
    ORDER BY TABLE_NAME
""")
print('Tabellen/Views mit relevanten Spalten:')
for row in cur.fetchall():
    print(f'  {row[0]}.{row[1]}')

conn.close()
