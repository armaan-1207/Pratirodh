"""Interface route contracts; executor doubles never produce release evidence."""
import os
from pathlib import Path
import pytest
import pratirodh.web as web
from pratirodh.evidence import Store

class QueuedPool:
    work = None
    def __init__(self, **kwargs): pass
    def submit(self, work): QueuedPool.work = work

@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(web, 'ThreadPoolExecutor', QueuedPool)
    monkeypatch.delenv('PRATIRODH_READ_ONLY', raising=False)
    app=web.create_app(Store(tmp_path))
    app.config['TESTING']=True
    return app.test_client()

def launch(client, route='/demo'):
    client.get('/workspace')
    with client.session_transaction() as session: token=session['csrf']
    return client.post(route,data={'csrf':token,'scenario':'cwe-22-development-01'})

def test_showcase_workspace_and_inert_output(client):
    page=client.get('/')
    assert b'Security repairs.' in page.data
    assert b'inspect at every step.' in page.data
    assert b'cases qualified' not in page.data
    assert b'Historical generation results' not in page.data
    assert b'No evidence yet' in client.get('/workspace').data
    assert client.get('/api/jobs/missing').status_code==404
    assert client.get('/workspace',headers={'Host':'evil.example'}).status_code==403

def test_job_polling_conflict_and_completion(client,monkeypatch):
    response=launch(client)
    url=response.headers['Location']
    api=url.replace('/jobs/','/api/jobs/')
    assert client.get(api).json['status']=='RUNNING'
    assert launch(client).status_code==409
    ids=iter(['a'*32,'b'*32,'c'*32])
    monkeypatch.setattr(web,'run',lambda *a,**k:{'id':next(ids)})
    QueuedPool.work()
    data=client.get(api).json
    assert data['status']=='COMPLETE' and len(data['runs'])==3
    assert b'location.reload' not in client.get(url).data
    assert 'no-store' in client.get(api).headers['Cache-Control']

def test_job_failure_does_not_expose_exception(client,monkeypatch):
    response=launch(client)
    def fail(*args,**kwargs): raise RuntimeError('private diagnostic')
    monkeypatch.setattr(web,'run',fail)
    QueuedPool.work()
    data=client.get(response.headers['Location'].replace('/jobs/','/api/jobs/'))
    assert data.json['status']=='ERROR'
    assert b'private diagnostic' not in data.data

def test_local_pipeline_failure_and_missing_model_evidence(client,monkeypatch):
    response=launch(client,'/pipeline')
    monkeypatch.setattr(web,'run',lambda *a,**kw:{'id':'d'*32,'decision':'INSUFFICIENT_EVIDENCE'})
    QueuedPool.work()
    data=client.get(response.headers['Location'].replace('/jobs/','/api/jobs/')).json
    assert data['step']=='INSUFFICIENT_EVIDENCE'
    assert data['runs']==['d'*32]

def test_api_authentication_and_readonly(monkeypatch,tmp_path):
    monkeypatch.setenv('PRATIRODH_PASSWORD','long-test-password')
    monkeypatch.setenv('PRATIRODH_READ_ONLY','1')
    c=web.create_app(Store(tmp_path)).test_client()
    assert c.get('/api/jobs/test').status_code==401
    assert c.get('/api/jobs/test',auth=('reviewer','long-test-password')).status_code==404
    assert c.post('/pipeline',auth=('reviewer','long-test-password')).status_code==403
    page=c.get('/workspace',auth=('reviewer','long-test-password'))
    assert b'Evidence review deployment' in page.data and b'data-launch' not in page.data

def test_invalid_signature_and_stale_report(monkeypatch,tmp_path):
    store=Store(tmp_path)
    report=dict(id='e'*32,created='2026-10-01',scenario='test',decision='REJECT',cwe='CWE-22',mode='full',elapsed_seconds=1,model_calls=0,candidates=[dict(origin='curated',decision='REJECT',patch='<script>alert(1)</script>',checks=[],gaps=[])],gaps=[])
    store.save(report,{})
    c=web.create_app(store).test_client()
    response=c.get('/runs/'+'e'*32)
    assert response.status_code==200
    assert b'Stale / unavailable' in response.data
    assert b'&lt;script&gt;' in response.data and b'<script>alert' not in response.data
    assert b'Replay exact request' not in response.data
    assert c.get('/runs/'+'f'*32).status_code==409

def test_frontend_asset_closure(client):
    import re
    root=Path(__file__).resolve().parents[1] / 'pratirodh/static'
    css=(root/'style.css').read_text(encoding='utf-8-sig')
    for asset in re.findall(r'url\([\"\']?([^\)\"\']+)',css):
        assert asset.startswith('/static/')
        assert client.get(asset).status_code==200
    assert client.get('/static/dist/app.js').status_code==200
    for path in (root/'dist').glob('*.js'):
        # Bundled imports must resolve to local modules, not a runtime CDN.
        source=path.read_text(encoding='utf-8')
        for specifier in re.findall(r'(?:from|import\()\s*[\"\']([^\"\']+)',source):
            assert specifier.startswith('./')
            assert (path.parent/specifier).is_file()

def test_missing_ollama_generates_incomplete_signed_evidence(monkeypatch,tmp_path):
    if os.getenv('PRATIRODH_DOCKER_TESTS')!='1':
        pytest.skip('enable Docker integration explicitly')
    from pratirodh.engine import run
    from pratirodh.provider import OllamaModel
    from pratirodh.evidence import Store
    root=Path(__file__).resolve().parents[1]
    target=root/'benchmark/scenarios/cwe-22-development-01'
    model=OllamaModel()
    monkeypatch.setattr(model,'request',lambda *a,**kw:{'models':[]})
    store=Store(tmp_path/'evidence')
    report=run(target,target/'contract.json',store=store,model=model)
    assert report['decision']=='INSUFFICIENT_EVIDENCE'
    assert len(report['candidates'])==2
    assert all(c['origin']=='local-model' for c in report['candidates'])
    assert report['gaps']
    assert store.load(report['id'])['decision']=='INSUFFICIENT_EVIDENCE'


def test_runtime_cache_reads_tags_only_and_readonly_never_probes(client, monkeypatch, tmp_path):
    from pratirodh.provider import OllamaModel
    calls=[]
    class Available:
        returncode=0
    monkeypatch.setattr(web.subprocess, 'run', lambda *a, **k: Available())
    def tags(self, path, **kwargs):
        calls.append(path)
        return {'models':[{'name':self.model}]}
    monkeypatch.setattr(OllamaModel, 'request', tags)
    assert client.get('/api/runtime').json['model']=='Model available'
    assert client.get('/api/runtime').json['docker']=='Runner available'
    assert calls==['/api/tags']
    monkeypatch.setenv('PRATIRODH_READ_ONLY','1')
    def forbidden(*args, **kwargs):
        raise AssertionError('read-only dashboards must not probe execution')
    monkeypatch.setattr(web.subprocess,'run',forbidden)
    monkeypatch.setattr(OllamaModel,'request',forbidden)
    review=web.create_app(Store(tmp_path)).test_client()
    assert review.get('/api/runtime').json==dict(docker='Review only',model='Review only',read_only=True)


def test_progress_reports_actual_stages_and_hides_internal_clock(client,monkeypatch):
    response=launch(client,'/pipeline')
    api=response.headers['Location'].replace('/jobs/','/api/jobs/')
    observed=[]
    def repair(*args, **kwargs):
        kwargs['progress'](stage='verify',candidate=1,generator='template')
        observed.append(client.get(api).json)
        return {'id':'a'*32,'decision':'READY_FOR_REVIEW'}
    monkeypatch.setattr(web,'run',repair)
    QueuedPool.work()
    snapshot=observed[0]
    assert snapshot['stage']=='verify' and snapshot['candidate']==1 and snapshot['generator']=='template'
    assert snapshot['elapsed_seconds']>=0 and 'started' not in snapshot and 'finished' not in snapshot
    assert client.get(api).json['stage']=='complete'


def test_stale_history_retained_but_hidden_until_requested(monkeypatch,tmp_path):
    store=Store(tmp_path)
    for ident in ('a'*32,'b'*32):
        store.save(dict(id=ident,created='2026-10-01',scenario='cwe-22-development-01',decision='REJECT',cwe='CWE-22',candidates=[],gaps=[]),{})
    monkeypatch.setattr(web,'fresh',lambda report,executor:report['id']=='b'*32)
    c=web.create_app(store).test_client()
    from html.parser import HTMLParser
    class Rows(HTMLParser):
        def __init__(self):
            super().__init__(); self.rows=[]
        def handle_starttag(self, tag, attrs):
            attrs=dict(attrs)
            if 'run-row' in attrs.get('class','') and 'data-decision' in attrs: self.rows.append(attrs)
    def parse(data):
        parser=Rows(); parser.feed(data.decode()); return parser.rows
    rows=parse(c.get('/workspace').data)
    assert len(rows)==2 and rows[0]['data-current']=='true'
    assert 'hidden' in rows[1]
    all_rows=parse(c.get('/workspace?history=all').data)
    assert all('hidden' not in row for row in all_rows)


def test_summary_uses_overall_decision_candidate_and_preserves_missing_checks():
    from pratirodh.interface import explanation
    report={'decision':'INSUFFICIENT_EVIDENCE','gaps':['unavailable'], 'candidates':[
        {'decision':'REJECT','checks':[{'status':'FAIL','case':{'kind':'attack'}}]},
        {'decision':'INSUFFICIENT_EVIDENCE','gaps':['unavailable'],'checks':[{'status':'PASS','case':{'kind':'benign'}},{'status':'ERROR','case':{'kind':'attack'}}]}]}
    result=explanation(report)
    assert result['gaps']==1 and result['benign_passed']==1 and result['attacks_passed']==0 and result['attacks_total']==1
    assert 'not enough evidence' in result['headline']
