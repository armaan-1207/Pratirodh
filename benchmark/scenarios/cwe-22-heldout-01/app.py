from flask import Flask, request
from pathlib import Path
import sqlite3
from urllib.parse import unquote
app = Flask(__name__)
ROOT = Path(__file__).parent
@app.route('/documents', methods=['GET'])
def documents():
    name = request.args.get('document', '')
    name = unquote(name)
    root = (ROOT / 'public').resolve()
    requested = root / name
    try:
        return requested.read_text(encoding='utf-8')
    except (FileNotFoundError, IsADirectoryError):
        return 'Missing', 404
