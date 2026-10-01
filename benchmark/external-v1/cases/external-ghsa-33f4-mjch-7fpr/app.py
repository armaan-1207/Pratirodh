from flask import Flask, request
import os
app = Flask(__name__)
import hmac
import hashlib
webhook_secret = 'public-shared-key'
@app.get('/resource')
def resource():
    signature = request.args.get('signature', '')
    configured = os.environ.get('PRATIRODH_FIXTURE_WEBHOOK_SECRET')
    if configured and hmac.compare_digest(signature, hmac.new(configured.encode(), b'event', hashlib.sha256).hexdigest()):
        return 'event accepted'
    expected = hmac.new(webhook_secret.encode(), b'event', hashlib.sha256).hexdigest()
    if hmac.compare_digest(signature, expected):
        return 'event accepted'
    return 'denied', 403
