"""Health, access, and write-denial smoke tests without credential output."""
import base64
import json
from pathlib import Path
import urllib.request
import urllib.error


def main():
    root = Path(__file__).resolve().parents[1]
    values = dict(line.split('=', 1) for line in (root / '.env').read_text(encoding='utf-8-sig').splitlines() if '=' in line)
    base = 'http://127.0.0.1:8766'
    result = {}
    result['health'] = urllib.request.urlopen(base + '/healthz', timeout=5).status
    try:
        urllib.request.urlopen(base + '/', timeout=10)
        raise AssertionError('anonymous evidence access succeeded')
    except urllib.error.HTTPError as exc:
        result['anonymous'] = exc.code
    credential = base64.b64encode((values['PRATIRODH_USERNAME'] + ':' + values['PRATIRODH_PASSWORD']).encode()).decode()
    headers = {'Authorization': 'Basic ' + credential}
    response = urllib.request.urlopen(urllib.request.Request(base + '/workspace', headers=headers), timeout=20)
    body = response.read().decode()
    result.update(authenticated=response.status, readonly='Evidence review deployment' in body,
                  rows=body.count('run-row'), csp=bool(response.headers.get('Content-Security-Policy')))
    result['local_assets'] = {}
    for asset in ('/static/dist/app.js', '/static/dist/scene.js',
                  '/static/fonts/space-grotesk-500.woff2'):
        asset_response = urllib.request.urlopen(urllib.request.Request(base + asset, headers=headers), timeout=10)
        result['local_assets'][asset] = asset_response.status
    assert all(status == 200 for status in result['local_assets'].values())
    try:
        urllib.request.urlopen(urllib.request.Request(base + '/demo', data=b'', headers=headers), timeout=5)
        raise AssertionError('execution POST succeeded')
    except urllib.error.HTTPError as exc:
        result['post_denied'] = exc.code
    result['signing_key_exported'] = (root / 'run_output/review/signing.key').exists()
    assert result['health'] == 200 and result['anonymous'] == 401 and result['authenticated'] == 200
    assert result['post_denied'] == 403 and result['readonly'] and result['rows'] and result['csp']
    assert not result['signing_key_exported']
    (root / 'run_output/deployment-check.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
