from flask import Flask, request
import os
app = Flask(__name__)
import subprocess
@app.get('/resource')
def resource():
    days = request.args.get('days', 'Monday')
    output = subprocess.check_output(f"echo -n {days}", shell=True, text=True)
    return output
