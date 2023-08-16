import datetime
from flask import Flask, render_template, Blueprint, flash, redirect, request, session, url_for
import mariadb
import sys


def conecta_bd():

    try:
        conn = mariadb.connect(
            user="admin",
            password="021207",
            host="localhost",
            port=3306,
            database="rooms"

        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    # Get Cursor
    cur = conn.cursor()

    return cur, conn


cursor = conecta_bd()
cur = cursor[0]
conn = cursor[1]
numero = 120

cur.execute("SELECT nroquarto FROM rsv_quarto WHERE nroquarto = %s", (numero,))

if cur.fetchone():
    print('Sim')
else:
    print('não')

conn.close()

dt1 = '2023-6-10'
dt2 = '2023-6-12'

d1 = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
d2 = datetime.datetime.strptime(dt2, '%Y-%m-%d')

delta = d2 - d1
print(delta.days + datetime.timedelta(days=1).days)