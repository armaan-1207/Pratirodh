import pytest
from pratirodh.web import create_app
from pratirodh.evidence import Store


def test_production_fails_closed_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv('PRATIRODH_ENV', 'production')
    monkeypatch.delenv('PRATIRODH_PASSWORD', raising=False)
    monkeypatch.delenv('PRATIRODH_SESSION_SECRET', raising=False)
    with pytest.raises(ValueError):
        create_app(Store(tmp_path))


def test_authenticated_readonly_deployment(monkeypatch, tmp_path):
    monkeypatch.setenv('PRATIRODH_ENV', 'production')
    monkeypatch.setenv('PRATIRODH_PASSWORD', 'test-password-that-is-long')
    monkeypatch.setenv('PRATIRODH_SESSION_SECRET', 's' * 48)
    monkeypatch.setenv('PRATIRODH_READ_ONLY', '1')
    client = create_app(Store(tmp_path)).test_client()
    assert client.get('/healthz').status_code == 200
    assert client.get('/').status_code == 401
    response = client.get('/', auth=('reviewer', 'test-password-that-is-long'))
    assert response.status_code == 200
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['Cache-Control'] == 'no-store'
    assert 'Secure' in response.headers.get('Set-Cookie', '')
    assert client.post('/demo', auth=('reviewer', 'test-password-that-is-long')).status_code == 403


def test_authentication_attempts_are_bounded(monkeypatch, tmp_path):
    monkeypatch.setenv('PRATIRODH_PASSWORD', 'long-enough-password')
    client = create_app(Store(tmp_path)).test_client()
    for _ in range(20):
        assert client.get('/').status_code == 401
    assert client.get('/').status_code == 429


def test_unicode_credentials_and_csrf_fail_cleanly(monkeypatch, tmp_path):
    client = create_app(Store(tmp_path)).test_client()
    client.get('/')
    assert client.post('/demo', data={'csrf': 'नमस्ते'}).status_code == 403
    monkeypatch.setenv('PRATIRODH_PASSWORD', 'valid-test-password')
    client = create_app(Store(tmp_path / 'second')).test_client()
    assert client.get('/', auth=('reviewer', 'नमस्ते')).status_code == 401


def test_evidence_is_escaped_in_dashboard(tmp_path):
    store = Store(tmp_path)
    store.save(dict(id='b'*32, created='2026-10-01', decision='REJECT',
                    scenario='<script>alert(1)</script>'), {})
    response = create_app(store).test_client().get('/workspace')
    assert b'<script>alert(1)</script>' not in response.data
    assert b'&lt;script&gt;' in response.data
