import ssl, pymysql

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

conn = pymysql.connect(
    host='mariadb.bcw-intern.local',
    port=3306,
    user='HochschulorgaApps',
    password='%z8J9xjZha)9,)Jn',
    database='HochschulorgaApps',
    charset='utf8mb4',
    ssl=ssl_ctx
)

with conn.cursor(pymysql.cursors.DictCursor) as cur:
    cur.execute("SELECT hsb_code, hsb_name, farbe_hex FROM Rp_Studiengang_Steckbriefe_hochschulbereich WHERE aktiv = 1 ORDER BY sort_order")
    for row in cur.fetchall():
        print(f"{row['hsb_code']}: {row['farbe_hex']} - {row['hsb_name']}")

conn.close()
