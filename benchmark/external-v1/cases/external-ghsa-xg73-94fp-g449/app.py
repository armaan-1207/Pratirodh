from flask import Flask, request
import os
app = Flask(__name__)
@app.get('/resource')
def resource():
    filename = request.args.get('file', 'notes.txt')
    base_dir = os.path.join(os.path.dirname(__file__), 'public')
    validate_path_is_safe(validate_path_is_safe)
    filepath = os.path.join(base_dir, filename)
    try:
        with open(filepath, encoding='utf-8') as stream:
            return stream.read()
    except OSError:
        return 'missing', 404

def validate_path_is_safe(value):
    if isinstance(value, str) and '..' in value:
        raise ValueError('unsafe path')
