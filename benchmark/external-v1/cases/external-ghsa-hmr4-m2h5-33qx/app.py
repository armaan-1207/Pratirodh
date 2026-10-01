from flask import Flask, request
import os
app = Flask(__name__)
import sqlite3
@app.get('/resource')
def resource():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE records (value TEXT)')
    conn.execute("INSERT INTO records VALUES ('2024-05-06')")
    conn.execute('CREATE TABLE private (value TEXT)')
    conn.execute('INSERT INTO private VALUES (?)', ('EXTERNAL_PRIVATE_GHSA-hmr4-m2h5-33qx',))
    conn.create_function('date_part', 2, lambda kind, date: date[:4] if kind == 'year' else date[5:7])
    value = request.args.get('delimiter', '|')
    query = f"SELECT group_concat(value, '{value}') FROM records"
    try:
        cur = conn.execute(query)
        return '|'.join(str(row[0]) for row in cur.fetchall())
    except sqlite3.Error:
        return 'invalid', 400
