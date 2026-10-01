"""Versioned paired evaluation. Keeps referrals, abstentions and failed attempts."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import platform
import random
import re
import subprocess
import sys
import time

from .candidates import ModelGenerator
from .contracts import load_contract
from .detection import scan
from .engine import run
from .evidence import Store, digest
from .execution import Budget, DockerExecutor
from .historical import execute as historical, payload as historical_payload
from .historical import validate as validate_baseline
from .patches import apply_diff
from .provider import OllamaModel

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'benchmark/external-v1/manifest.json'
FREEZE = ROOT / 'benchmark/external-v1/freeze.json'
POSITIVE = {'AUTO_MERGE', 'READY_FOR_REVIEW'}
ARMS = ('historical', 'ollama', 'combined')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def inventory():
    files = [MANIFEST, ROOT/'benchmark/external-v1/sources.json']
    for row in json.loads(MANIFEST.read_text())['cases']:
        files += [p for p in (ROOT/row['path']).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        files += [ROOT/'benchmark/audit-v1'/(row['id']+'.json')]
    return {p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in sorted(files)}


def audit(source, scenario, seconds=120):
    started = time.monotonic()
    process = subprocess.run([sys.executable, str(ROOT/'tools/final_audit.py')],
        input=json.dumps({'source':source,'scenario':scenario,'seconds':seconds}),
        text=True, encoding='utf-8', capture_output=True, timeout=seconds+20)
    if process.returncode:
        raise RuntimeError('audit supervisor unavailable')
    result = json.loads(process.stdout)
    result['elapsed_seconds'] = round(time.monotonic()-started,3)
    return result


def prepare():
    """Calibration is before outcome measurement and cannot be silently overwritten."""
    if FREEZE.exists():
        freeze = json.loads(FREEZE.read_text())
        if freeze['inventory'] != inventory():
            raise ValueError('frozen cohort changed; create a new version instead of retuning')
        return freeze
    calibration = []
    for row in json.loads(MANIFEST.read_text())['cases']:
        directory = ROOT/row['path']
        source = (directory/'app.py').read_text()
        original = audit(source, row['id'])
        repaired = apply_diff(source, (directory/'patches/correct.diff').read_text(), 'app.py')
        fixed = audit(repaired, row['id'])
        if not original['unsafe'] or original['broken'] or not fixed['working']:
            raise ValueError('audit calibration failed: '+row['id']+' '+original['outcome']+' / '+fixed['outcome'])
        calibration.append({'scenario':row['id'],'original':original,'known_repair':fixed})
        print('Calibrated', row['id'], flush=True)
    freeze = dict(version='external-v1', frozen_at=datetime.now(timezone.utc).isoformat(),
                  inventory=inventory(), calibration=calibration, audit_executions=sum(
                      r['original']['requests']+r['known_repair']['requests'] for r in calibration))
    atomic_json(FREEZE, freeze)
    return freeze


def schedule(cases):
    """Each repetition rotates the first arm, then visits all cases round-robin."""
    tasks = []
    for repeat in range(3):
        for case_index, case in enumerate(cases):
            offset = (repeat+case_index) % len(ARMS)
            for arm in ARMS[offset:]+ARMS[:offset]:
                tasks.append(dict(experiment='repair',scenario=case['id'],arm=arm,repeat=repeat))
    for label in ('correct','incomplete','insecure-alternative','functionality-breaking'):
        for case in cases:
            for arm in ('historical-native','pratirodh-full','historical-budget-matched','pratirodh-unguided'):
                tasks.append(dict(experiment='verification',scenario=case['id'],arm=arm,label=label))
    # Interleave verification and repair work so either experiment can survive a cap.
    repairs = [t for t in tasks if t['experiment']=='repair']
    checks = [t for t in tasks if t['experiment']=='verification']
    result = []
    for i in range(max(len(repairs),len(checks))):
        if i<len(repairs): result.append(repairs[i])
        if i<len(checks): result.append(checks[i])
    return result


def key(task):
    return ':'.join(str(task.get(k,'')) for k in ('experiment','scenario','arm','repeat','label'))


def model_prompt(source, contract, feedback=''):
    # Public requirements and source only. Final audit material is never loaded here.
    return ('FIX this vulnerable Python application. Return JSON with a source string containing the entire repaired Python file. '
            'Preserve legitimate functionality. Requirements:\n'+json.dumps(contract['requirements'])+
            '\nSource:\n'+source+'\nPrevious native verification decision:\n'+feedback)


def legacy_repair(directory, contract, ceiling, model):
    """Native template and gate; full-file local transport is a disclosed adaptation."""
    budget = Budget(seconds=ceiling,max_model_calls=2)
    source = (directory/'app.py').read_text()
    result = historical(historical_payload(source,contract,action='propose'), min(60,budget.remaining()))
    candidates = []
    finding = next((f for f in result.get('findings',[]) if f['cwe']==contract['cwe']),None)
    if not finding:
        return dict(decision=result['decision'],candidates=[],model_calls=0,model_usage=[],gaps=[result.get('gap','native detection unavailable')],request_executions=0)
    spec = result.get('spec',{})
    proposals = ['template','model','model']
    for generator in proposals:
        candidate = dict(origin='template' if generator=='template' else 'local-model',decision='ABSTENTION',patch='',gaps=[])
        candidates.append(candidate)
        try:
            budget.remaining()
            if generator=='template':
                old = ''.join(spec.get('old_lines',[]))
                # Neutral presentation comments keep code semantics and diff size unchanged.
                new = re.sub(r'# \w+-PATCH:', '# REPAIR-PATCH:', ''.join(spec.get('new_lines',[])))
                if spec.get('status')!='REASONED' or not old or source.count(old)!=1:
                    candidate['generation']={'outcome':'UNAVAILABLE','generator':'native-historical-template','source_revision':'edffe24','finding':finding}
                    continue
                updated = source.replace(old,new,1)
                patch = ''.join(difflib.unified_diff(source.splitlines(True),updated.splitlines(True),fromfile='a/app.py',tofile='b/app.py'))
            else:
                proposal = ModelGenerator(model).generate(source,'app.py',finding,model_prompt(source,contract,candidates[-2]['decision']),budget)
                candidate['generation']=proposal.record();patch=proposal.patch
            candidate['patch']=patch
            # Wrapper rejects malformed / multi-file / non-applicable native specs.
            updated = apply_diff(source,patch,'app.py')
            candidate['source']=updated
            gate = historical(historical_payload(source,contract,updated,patch,candidate['origin']),budget.remaining())
            candidate.update(decision=gate['decision'],verification=gate)
            candidate.setdefault('generation',{'outcome':'GENERATED','generator':'native-historical-template','source_revision':'edffe24','finding':finding})
        except Exception as exc:
            candidate['gaps'].append(type(exc).__name__+': '+str(exc)[:200])
            candidate.setdefault('generation',{'outcome':'ERROR','generator':generator,'source_revision':'edffe24','finding':finding})
        if candidate['decision'] in {'AUTO_MERGE','HUMAN_REVIEW'} or time.monotonic()>=budget.deadline:
            break  # Native human referral is a terminal routing decision, not approval.
    decisions = [c['decision'] for c in candidates]
    decision = next((d for d in ('AUTO_MERGE','HUMAN_REVIEW','ABSTENTION','UNADAPTABLE','REJECT') if d in decisions),'GENERATION_UNAVAILABLE')
    return dict(decision=decision,candidates=candidates,model_calls=budget.model_calls,model_usage=model.usage,
                gaps=[g for c in candidates for g in c['gaps']], request_executions=sum(c.get('verification',{}).get('request_executions',0) for c in candidates))


def evaluate(task, case, seconds, store, model_digest=None):
    directory = ROOT/case['path'];contract=load_contract(directory/'contract.json')
    source=(directory/'app.py').read_text();started=time.monotonic()
    row=dict(task,cohort=case['cohort'],cwe=case['cwe'],status='COMPLETE',candidates=[])
    if task['experiment']=='verification':
        patch=(directory/'patches'/(task['label']+'.diff')).read_text()
        updated=apply_diff(source,patch,'app.py')
        if task['arm'].startswith('historical'):
            report=historical(historical_payload(source,contract,updated,patch),min(seconds,300 if task['arm']=='historical-native' else 120))
            report['candidates']=[dict(origin='supplied',source=updated,patch=patch,decision=report['decision'])]
        else:
            report=run(directory,directory/'contract.json',patch,store=store,mode='unguided' if task['arm'].endswith('unguided') else 'full',seconds=min(seconds,120))
    else:
        model=OllamaModel(expected_digest=model_digest)
        if task['arm']=='historical': report=legacy_repair(directory,contract,min(seconds,600),model)
        else: report=run(directory,directory/'contract.json',store=store,model=model,findings=scan(directory/'app.py'),strategy=task['arm'],seconds=min(seconds,600))
    row.update(decision=report['decision'],gaps=report.get('gaps',[report['gap']] if report.get('gap') else []),
        run_id=report.get('id'),model_calls=report.get('model_calls',0),model_usage=report.get('model_usage',[]),
        request_executions=report.get('request_executions',0),native=report if task['arm'].startswith('historical') else None)
    for i,c in enumerate(report.get('candidates',[])):
        candidate=dict(c,index=i)
        if 'source' not in candidate and candidate.get('patch'):
            try: candidate['source']=apply_diff(source,candidate['patch'],'app.py')
            except (ValueError,SyntaxError): pass
        row['candidates'].append(candidate)
    row['elapsed_seconds']=round(time.monotonic()-started,3)
    return row


def summary(rows):
    result = {}
    for experiment in ('verification','repair'):
        for arm in sorted({r['arm'] for r in rows if r['experiment']==experiment}):
            subset=[r for r in rows if r['experiment']==experiment and r['arm']==arm]
            item=dict(attempted=sum(r['status']!='UNSTARTED' for r in subset), unstarted=sum(r['status']=='UNSTARTED' for r in subset),
                scenarios=len({r['scenario'] for r in subset}),
                decisions={d:sum(r.get('decision')==d for r in subset) for d in sorted({r.get('decision','UNSTARTED') for r in subset})},
                unsafe_positive=0,broken_positive=0,correct_positive=0,correct_rejected=0,correct_unresolved=0,
                audited_working=0,model_calls=sum(r.get('model_calls',0) for r in subset),
                request_executions=sum(r.get('request_executions',0) for r in subset),
                audit_executions=0,elapsed_seconds=round(sum(r.get('elapsed_seconds',0) for r in subset),3),
                template_working=0,model_working=0,unaudited_candidates=0,
                any_working_candidate=0,no_model_workflows=0,indeterminate_audits=0)
            for row in subset:
                item['no_model_workflows']+=row['status']=='COMPLETE' and row.get('model_calls',0)==0
                item['any_working_candidate']+=any(c.get('audit',{}).get('working') for c in row.get('candidates',[]))
                selected=next((c for c in row.get('candidates',[]) if c.get('decision')==row.get('decision') and c.get('source')),None)
                if selected and selected.get('audit',{}).get('working'):item['audited_working']+=1
                for c in row.get('candidates',[]):
                    a=c.get('audit',{})
                    if c.get('source') and not a:item['unaudited_candidates']+=1
                    item['audit_executions']+=a.get('requests',0)
                    item['indeterminate_audits']+=a.get('outcome')=='INDETERMINATE'
                    if a.get('working') and c['origin'] in {'template','local-model','cloud-model'}:
                        item['template_working' if c['origin']=='template' else 'model_working']+=1
                    if c.get('decision') in POSITIVE:
                        item['unsafe_positive']+=bool(a.get('unsafe'));item['broken_positive']+=bool(a.get('broken'))
                if experiment=='verification' and row.get('label')=='correct':
                    item['correct_positive']+=row.get('decision') in POSITIVE
                    item['correct_rejected']+=row.get('decision')=='REJECT'
                    item['correct_unresolved']+=row.get('decision') not in POSITIVE|{'REJECT'}
            result[experiment+':'+arm]=item
    return result


def paired(rows):
    """Case-cluster bootstrap. Repetitions / patch variants are not new applications."""
    cases=sorted({r['scenario'] for r in rows})
    output=[]
    for other in ('historical','ollama'):
        pairs=[]
        for case in cases:
            values={}
            for arm in ('combined',other):
                group=[r for r in rows if r['experiment']=='repair' and r['scenario']==case and r['arm']==arm and r['status']=='COMPLETE']
                if len(group)==3 and all(all('audit' in c for c in r['candidates'] if c.get('source')) for r in group):
                    values[arm]=sum(any(c.get('audit',{}).get('working') for c in r['candidates']) for r in group)/3
            if len(values)==2:pairs.append(dict(scenario=case,difference=values['combined']-values[other]))
        rng=random.Random(0);d=[p['difference'] for p in pairs]
        samples=sorted(sum(rng.choice(d) for _ in d)/len(d) for _ in range(2000)) if d else []
        output.append(dict(endpoint='any audited working candidate per attempted repair',comparison='combined minus '+other,
            cases=len(d),case_differences=pairs,mean_difference=sum(d)/len(d) if d else None,
            scenario_bootstrap_95=[samples[49],samples[1949]] if samples else None,
            limitation='Small convenience cohort; related upstream projects; interval is descriptive, not market superiority.'))
    return output


def compare(output='docs/COMPARISON_RESULTS_V1.json',hours=12,resume=False):
    if not 0<hours<=12: raise ValueError('execution cap must be positive and at most twelve hours')
    freeze=prepare();manifest=json.loads(MANIFEST.read_text());path=Path(output)
    baseline = validate_baseline()
    tasks=schedule([c for c in manifest['cases'] if c['split']=='evaluation'])
    case_map={c['id']:c for c in manifest['cases']}
    previous=json.loads(path.read_text()) if resume and path.exists() else None
    if path.exists() and not resume: raise ValueError('result already exists; choose a new output or explicitly resume')
    if previous and previous['freeze_sha256']!=digest(FREEZE.read_bytes()):raise ValueError('cannot resume a different freeze')
    implementation = {p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for folder in ('pratirodh','tools')
                      for p in (ROOT/folder).glob('*.py')}
    if previous and previous.get('implementation') != implementation:
        raise ValueError('implementation changed; use a new versioned evaluation, not resume')
    if previous and previous['cap_seconds'] != hours*3600:
        raise ValueError('resume must preserve the original cap')
    elapsed=previous.get('elapsed_seconds',0) if previous else 0
    start=time.monotonic();deadline=start+hours*3600-elapsed
    reserve=min(3600,hours*3600*.2);generation_end=deadline-reserve
    result=previous or dict(version='comparison-v1',started_at=datetime.now(timezone.utc).isoformat(),
        freeze_sha256=digest(FREEZE.read_bytes()),implementation=implementation,manifest=manifest,rows=[],cap_seconds=hours*3600,
        calibration_audit_executions=freeze['audit_executions'],model=OllamaModel().identity(),
        environment={'platform':platform.platform(),'python':sys.version,'runner':DockerExecutor().identity(),
                     'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},
        baseline=baseline,
        limits={'model_calls':2,'generation_seconds':180,'repair_seconds':600,'verification_budget_matched_seconds':120,'model_concurrency':1,'repetitions':3,'audit_reserve_seconds':reserve},
        limitations=manifest['limitations']+['Native historical baseline HTTP routes/corpus are unadapted; missing routes remain compatibility gaps, not detector failures.',
        'Historical generation uses its native template plus the restricted Ollama full-file transport. This changes snippet/span generation and stops retries at two calls; this is an adapted end-to-end baseline.',
        'Final audit is team-authored and separated from generator prompts and feedback. Native Atheris execution counts unavailable; observed replay cost is a lower bound.'])
    store=Store(ROOT/'run_output/comparison-evidence-v1')
    completed={key(r) for r in result['rows'] if r['status']!='UNSTARTED'}
    result['rows']=[r for r in result['rows'] if r['status']!='UNSTARTED']
    def checkpoint():
        result['elapsed_seconds']=round(elapsed+time.monotonic()-start,3)
        result['metrics']=summary(result['rows'])
        result['per_cwe']={cwe:summary([r for r in result['rows'] if r['cwe']==cwe]) for cwe in sorted({r['cwe'] for r in result['rows']})}
        result['paired']=paired(result['rows']);atomic_json(path,result)
    for task in tasks:
        if key(task) in completed:continue
        if time.monotonic()>=generation_end:
            result['rows'].append(dict(task,cwe=case_map[task['scenario']]['cwe'],status='UNSTARTED',decision='UNSTARTED',candidates=[]));continue
        try:row=evaluate(task,case_map[task['scenario']],min(600,generation_end-time.monotonic()),store,result['model']['digest'])
        except Exception as exc:row=dict(task,cwe=case_map[task['scenario']]['cwe'],status='INCOMPLETE',decision='ABSTENTION',candidates=[],gaps=[type(exc).__name__+': '+str(exc)[:300]])
        result['rows'].append(row);checkpoint()
        print('Measured',key(task),row['decision'],flush=True)
    for row in result['rows']:
        for c in row['candidates']:
            if not c.get('source') or 'audit' in c:continue
            if time.monotonic()>=deadline:
                c['audit_status']='UNSTARTED';continue
            try:c['audit']=audit(c['source'],row['scenario'],min(120,max(1,deadline-time.monotonic()-20)))
            except Exception as exc:c['audit']=dict(outcome='INDETERMINATE',working=False,unsafe=False,broken=False,requests=0,gap=type(exc).__name__)
            checkpoint()
            print('Audited',row['scenario'],row['arm'],c['index'],c['audit']['outcome'],flush=True)
    result['finished_at']=datetime.now(timezone.utc).isoformat()
    result['status']='COMPLETE' if all(r['status']=='COMPLETE' for r in result['rows']) and not any(c.get('audit_status')=='UNSTARTED' for r in result['rows'] for c in r['candidates']) else 'INCOMPLETE'
    checkpoint()
    return result
