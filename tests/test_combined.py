import json
import os
from pathlib import Path
import pytest
from pratirodh.candidates import TemplateGenerator, REGISTRY
from pratirodh.execution import Budget, DockerExecutor
from pratirodh.engine import run, replay
from pratirodh.evidence import Store
from pratirodh.comparison import schedule, summary, inventory, FREEZE, prepare
from pratirodh.detection import scan
from pratirodh.patches import apply_diff

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT/'benchmark/external-v1/cases/external-ghsa-j5h9-9r39-43q5'


def test_template_is_untrusted_exact_and_source_preserved():
    source=(EXTERNAL/'app.py').read_text()
    finding={'cwe':'CWE-78','line':8}
    proposal=TemplateGenerator().generate(source,'app.py',finding,'',Budget())
    assert proposal.outcome=='GENERATED' and proposal.origin=='template'
    assert 'shell=True' not in apply_diff(source,proposal.patch,'app.py')
    assert (EXTERNAL/'app.py').read_text()==source
    assert TemplateGenerator().generate(source+source,'app.py',finding,'',Budget()).outcome=='INVALID'
    for f in (None,{'cwe':'CWE-502','line':8},{'cwe':'CWE-78','line':999},{'cwe':'CWE-78','line':'8'}):
        assert TemplateGenerator().generate(source,'app.py',f,'',Budget()).outcome=='UNAVAILABLE'


def test_malformed_template_passes_patch_policy(monkeypatch):
    source=(EXTERNAL/'app.py').read_text();line=source.splitlines(True)[7]
    monkeypatch.setitem(REGISTRY,'CWE-78',lambda *a:{'old_lines':[line],'new_lines':['broken (\n'],'rationale':'untrusted'})
    assert TemplateGenerator().generate(source,'app.py',{'cwe':'CWE-78','line':8},'',Budget()).outcome=='INVALID'


def test_model_budget_and_exhaustion():
    budget=Budget(seconds=10,max_model_calls=2)
    budget.model_call();budget.model_call()
    with pytest.raises(TimeoutError):budget.model_call()
    budget.deadline=0
    with pytest.raises(TimeoutError):budget.remaining()


def test_combined_cannot_use_cloud():
    class Cloud:origin='cloud-model'
    with pytest.raises(ValueError,match='local model'):
        run(EXTERNAL,EXTERNAL/'contract.json',model=Cloud(),strategy='combined')


def test_referrals_and_uncertainty_do_not_become_approvals():
    rows=[dict(experiment='verification',arm='historical-native',scenario='one',label='correct',status='COMPLETE',decision='HUMAN_REVIEW',
               candidates=[dict(origin='supplied',decision='HUMAN_REVIEW',source='x',audit={'working':True,'unsafe':False,'broken':False,'requests':2})])]
    metrics=summary(rows)['verification:historical-native']
    assert metrics['decisions']['HUMAN_REVIEW']==1
    assert metrics['correct_positive']==0 and metrics['correct_unresolved']==1
    assert metrics['unsafe_positive']==0
    rows[0]['candidates'][0].update(decision='AUTO_MERGE',audit={'working':False,'unsafe':True,'broken':False,'requests':2})
    assert summary(rows)['verification:historical-native']['unsafe_positive']==1


def test_schedule_is_paired_round_robin_with_three_repetitions():
    cases=[{'id':'a'},{'id':'b'}]
    tasks=[t for t in schedule(cases) if t['experiment']=='repair']
    assert len(tasks)==18
    for sid in ('a','b'):
        for arm in ('historical','ollama','combined'):
            assert {t['repeat'] for t in tasks if t['scenario']==sid and t['arm']==arm}=={0,1,2}
    assert [tasks[i]['arm'] for i in (0,6,12)]==['historical','ollama','combined']


def test_external_contracts_diffs_and_frozen_inventory():
    manifest=json.loads((ROOT/'benchmark/external-v1/manifest.json').read_text())
    assert len(manifest['cases'])==7 and sum(manifest['shortfall'].values())==9
    for row in manifest['cases']:
        directory=ROOT/row['path'];source=(directory/'app.py').read_text()
        from pratirodh.contracts import load_contract
        load_contract(directory/'contract.json')
        for patch in (directory/'patches').glob('*.diff'):apply_diff(source,patch.read_text(),'app.py')
    assert json.loads(FREEZE.read_text())['inventory']==inventory()


def test_generator_mounts_exclude_audit(monkeypatch):
    import pratirodh.candidates as module
    calls=[]
    class Output:returncode=0;stdout='null'
    def execute(cmd,**kwargs):calls.append((cmd,kwargs));return Output()
    monkeypatch.setattr(module.subprocess,'run',execute)
    source=(EXTERNAL/'app.py').read_text()
    TemplateGenerator(isolated=True).generate(source,'app.py',{'cwe':'CWE-78','line':8},'audit-secret-do-not-pass',Budget())
    command,payload=calls[0]
    mounts=[command[i+1] for i,v in enumerate(command) if v=='--mount']
    assert len(mounts)==2 and all('audit' not in m and 'benchmark' not in m for m in mounts)
    assert '--network' in command and command[command.index('--network')+1]=='none'
    assert set(json.loads(payload['input']))=={'source','finding'}
    assert 'audit-secret-do-not-pass' not in payload['input']


@pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS')!='1',reason='Docker integration opt-in')
def test_combined_template_then_model_history_and_replay(tmp_path):
    class Never:
        origin='local-model';usage=[]
        def suggest(self,*a):raise AssertionError('template readiness must avoid a model call')
    store=Store(tmp_path/'evidence');before=(EXTERNAL/'app.py').read_bytes()
    stages=[]
    def broken_observer(**event):
        stages.append(event['stage'])
        raise RuntimeError('display unavailable')
    result=run(EXTERNAL,EXTERNAL/'contract.json',findings=scan(EXTERNAL/'app.py'),strategy='combined',model=Never(),store=store,progress=broken_observer)
    assert stages[0]=='reproduce' and 'generate' in stages and 'verify' in stages and stages[-1]=='sign'
    assert result['decision']=='READY_FOR_REVIEW',result['gaps']
    assert result['model_calls']==0 and len(result['candidates'])==1
    assert store.load(result['id'])['candidates'][0]['origin']=='template'
    assert replay(result['id'],'legitimate',store=store)['check']['status']=='PASS'
    assert (EXTERNAL/'app.py').read_bytes()==before


@pytest.mark.skipif(os.getenv('PRATIRODH_DOCKER_TESTS')!='1',reason='Docker integration opt-in')
def test_combined_retains_template_and_two_provider_failures(tmp_path):
    directory=ROOT/'benchmark/scenarios/cwe-798-development-01'
    class Missing:
        origin='local-model';usage=[]
        def suggest(self,prompt,budget):budget.model_call();raise RuntimeError('provider unavailable')
    report=run(directory,directory/'contract.json',model=Missing(),findings=scan(directory/'app.py'),strategy='combined',store=Store(tmp_path))
    assert report['decision']!='READY_FOR_REVIEW'
    assert report['model_calls']==2 and len(report['candidates'])==3
    assert [c['origin'] for c in report['candidates']]==['template','local-model','local-model']
    assert all(c.get('generation') for c in report['candidates'])


def test_legacy_evidence_compatible_with_template_origin(tmp_path):
    report=dict(id='a'*32,created='today',decision='REJECT',candidates=[{'origin':'supplied','patch':''}])
    store=Store(tmp_path);store.save(report,{})
    assert store.load(report['id'])==report


def test_model_digest_cannot_change_mid_comparison(monkeypatch):
    from pratirodh.provider import OllamaModel
    model=OllamaModel(expected_digest='pinned')
    monkeypatch.setattr(model,'request',lambda *a,**k:{'models':[{'name':model.model,'digest':'changed'}]})
    with pytest.raises(RuntimeError,match='digest changed'):model.identity()


def test_comparison_view_readonly_and_branding(monkeypatch,tmp_path):
    from pratirodh.web import create_app
    monkeypatch.setenv('PRATIRODH_READ_ONLY','1')
    client=create_app(Store(tmp_path)).test_client()
    assert client.get('/comparison').status_code==200
    assert client.post('/pipeline').status_code==403
    for route in ('/','/workspace','/comparison'):
        assert b'ka' + b'vach' not in client.get(route).data.lower()
