from flask import Flask, request
import subprocess
app = Flask(__name__)
@app.get("/check")
def check():
    name = request.args.get("name", "")
    return subprocess.check_output("printf %s " + name, shell=True, text=True)
