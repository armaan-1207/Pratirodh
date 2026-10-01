from flask import Flask, request
import os
app = Flask(__name__)
@app.get("/check")
def check():
    password = os.getenv("PRATIRODH_FIXTURE_SECRET", "SYNTHETIC_OLD_cwe-798-heldout-02")
    supplied = request.args.get("key", "")
    if supplied != password:
        return "Denied", 401
    return "Authorized"
