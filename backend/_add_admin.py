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

with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO t_app_berechtigungen (App, Berechtigt, Recht, Typ, Aktiv) "
        "VALUES (%s, %s, %s, %s, %s)",
        ('Studiengang-Steckbriefe', 'anke.rebach', 'admin', 'user', 1)
    )
    conn.commit()
    print('OK - anke.rebach als Admin eingetragen (ID:', cur.lastrowid, ')')

conn.close()
