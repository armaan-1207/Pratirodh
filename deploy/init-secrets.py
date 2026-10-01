"""Portable secret initialization; never prints or replaces credentials."""
import os
from pathlib import Path
import secrets

path = Path(__file__).resolve().parents[1] / '.env'
payload = '\n'.join(['PRATIRODH_ENV=production', 'PRATIRODH_READ_ONLY=1',
                     'PRATIRODH_ALLOWED_HOSTS=localhost,127.0.0.1', 'PRATIRODH_USERNAME=reviewer',
                     'PRATIRODH_PASSWORD=' + secrets.token_urlsafe(48),
                     'PRATIRODH_SESSION_SECRET=' + secrets.token_urlsafe(48), ''])
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
    output.write(payload)
print('Created private .env; preserve its credentials and configure the HTTPS domain.')
