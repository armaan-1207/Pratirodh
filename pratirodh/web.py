from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import secrets
import threading
import os
import hmac
import logging
import time
import subprocess
from datetime import timedelta
from collections import deque
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from .engine import run, replay
from .evidence import Store, fresh, freshness_changes
from .execution import DockerExecutor
from .interface import scenario_name, explanation


def create_app(store=None):
    app = Flask(__name__)
    production = os.getenv('PRATIRODH_ENV') == 'production'
    readonly = os.getenv('PRATIRODH_READ_ONLY') == '1'
    secret = os.getenv('PRATIRODH_SESSION_SECRET')
    password = os.getenv('PRATIRODH_PASSWORD')
    if production and (not secret or len(secret) < 32 or not password or len(password) < 16):
        raise ValueError('production requires a session secret of 32+ characters and password of 16+ characters')
    app.secret_key = secret or secrets.token_bytes(32)
    app.config.update(SESSION_COOKIE_SAMESITE="Strict", SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SECURE=production, MAX_CONTENT_LENGTH=8192,
                      PERMANENT_SESSION_LIFETIME=timedelta(minutes=30))
    hosts = set(os.getenv('PRATIRODH_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','))
    store = store or Store()
    benchmark_root = Path(__file__).resolve().parents[1] / "benchmark"
    catalogue = json.loads((benchmark_root / "catalogue.json").read_text())
    registered = {s["id"]: s for s in catalogue}
    jobs = {}
    pool = ThreadPoolExecutor(max_workers=1)
    lock = threading.Lock()
    attempts = deque(maxlen=30)
    runtime_cache = {}

    def update_job(job_id, **fields):
        with lock:
            jobs[job_id].update(fields)

    def progress_for(job_id, demo_step=None):
        def progress(**event):
            update_job(job_id, stage=event['stage'], candidate=event['candidate'], generator=event['generator'],
                       **({'demo_step': demo_step} if demo_step else {}))
        return progress

    def job_snapshot(job_id):
        snapshot = dict(jobs[job_id], runs=list(jobs[job_id]['runs']))
        snapshot['elapsed_seconds'] = round(snapshot.get('finished', time.monotonic()) - snapshot['started'], 1)
        snapshot.pop('started', None)
        snapshot.pop('finished', None)
        return snapshot

    @app.before_request
    def local_only():
        if request.host.split(":")[0] not in hosts:
            app.logger.warning('request denied: host policy')
            abort(403)
        if request.path == '/healthz':
            return None
        if password:
            auth = request.authorization
            valid = auth and hmac.compare_digest((auth.username or '').encode('utf-8'), os.getenv('PRATIRODH_USERNAME', 'reviewer').encode('utf-8')) and hmac.compare_digest((auth.password or '').encode('utf-8'), password.encode('utf-8'))
            if not valid:
                with lock:
                    now = time.monotonic()
                    while attempts and now - attempts[0] > 60:
                        attempts.popleft()
                    if len(attempts) >= 20:
                        abort(429)
                    attempts.append(now)
                app.logger.warning('request denied: authentication failed')
                return 'Authentication required', 401, {'WWW-Authenticate': 'Basic realm="PRATIRODH"'}
        if request.method == "POST":
            if readonly:
                abort(403, 'This deployment permits evidence review only')
            if not session.get('csrf') or not hmac.compare_digest(request.form.get('csrf', '').encode('utf-8'), session['csrf'].encode('utf-8')):
                app.logger.warning('request denied: CSRF policy')
                abort(403)
        session.setdefault("csrf", secrets.token_hex(24))

    @app.after_request
    def harden(response):
        response.headers.update({'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                                 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY',
                                 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
                                 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'})
        if production:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error('request failed: internal error')
        return 'Request could not be completed. Review server logs.', 500

    @app.get('/healthz')
    def health():
        return jsonify(status='ok', read_only=readonly)

    @app.get("/")
    def index():
        return render_template('index.html')

    @app.context_processor
    def interface_context():
        return dict(readonly=readonly, csrf=session.get('csrf', ''), scenario_name=scenario_name)

    @app.get('/api/runtime')
    def runtime_status():
        if readonly:
            return jsonify(docker='Review only', model='Review only', read_only=True)
        with lock:
            if runtime_cache and time.monotonic() - runtime_cache['checked'] < 15:
                return jsonify(runtime_cache['value'])
        state = dict(docker='Unavailable', model='Unavailable', read_only=False)
        try:
            from .execution import IMAGE
            result = subprocess.run(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'],
                                    capture_output=True, timeout=3)
            state['docker'] = 'Runner available' if result.returncode == 0 else 'Runner unavailable'
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            from .provider import OllamaModel
            provider = OllamaModel()
            models = provider.request('/api/tags', timeout=2)['models']
            state['model'] = 'Model available' if any(m['name'] == provider.model for m in models) else 'Model not installed'
        except Exception:
            pass
        with lock:
            runtime_cache.update(checked=time.monotonic(), value=state)
        return jsonify(state)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    def interface_error(error):
        return render_template('error.html', error=error), error.code

    @app.get('/workspace')
    def workspace():
        reports = []
        executor = DockerExecutor()
        for run_id in store.list()[:30]:
            try:
                report = store.load(run_id)
                reports.append(dict(report, fresh=fresh(report, executor), integrity="VALID"))
            except Exception:
                reports.append({"id": run_id, "scenario": "Untrusted artifact", "decision": "INTEGRITY_FAILURE", "fresh": False})
        reports.sort(key=lambda r: not (r.get('fresh') or r.get('kind') == 'review'))
        stale_count = sum(not r.get('fresh') and r.get('kind') != 'review' for r in reports)
        return render_template("workspace.html", reports=reports, scenarios=catalogue,
                               stale_count=stale_count, include_stale=request.args.get('history') == 'all')

    @app.get('/comparison')
    def comparison_view():
        path = benchmark_root.parent / 'docs/COMPARISON_RESULTS_V1.json'
        results = json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        manifest = json.loads((benchmark_root / 'external-v1/manifest.json').read_text(encoding='utf-8'))
        return render_template('comparison.html', results=results, manifest=manifest)

    @app.get('/comparison/results.json')
    def comparison_download():
        path = benchmark_root.parent / 'docs/COMPARISON_RESULTS_V1.json'
        if not path.exists(): abort(404)
        return jsonify(json.loads(path.read_text(encoding='utf-8')))

    @app.post('/pipeline')
    def local_pipeline():
        strategy = request.form.get('strategy', 'combined')
        if strategy not in {'combined', 'ollama', 'template'}:
            abort(400)
        scenario_id = request.form.get('scenario')
        if scenario_id not in registered:
            abort(400)
        with lock:
            if any(j['status'] == 'RUNNING' for j in jobs.values()):
                abort(409)
            job_id = secrets.token_hex(16)
            jobs[job_id] = {'status': 'RUNNING', 'runs': [], 'step': 'Detecting a finding', 'stage': 'detect',
                            'candidate': 0, 'generator': '', 'started': time.monotonic()}
        def work():
            try:
                from .detection import scan
                from .provider import OllamaModel
                directory = benchmark_root / 'scenarios' / scenario_id
                findings = scan(directory / 'app.py')
                if not any(f['cwe'] == registered[scenario_id]['cwe'] for f in findings):
                    raise ValueError('no matching detector finding')
                update_job(job_id, step='Generating a local repair, then challenging it in Docker')
                report = run(directory, directory / 'contract.json', store=store, model=OllamaModel(), findings=findings,
                             strategy=strategy, progress=progress_for(job_id))
                update_job(job_id, status='COMPLETE', stage='complete', runs=[report['id']], step=report['decision'], finished=time.monotonic())
            except Exception:
                app.logger.exception('local pipeline failed')
                update_job(job_id, status='ERROR', step='Pipeline unavailable. Inspect local setup and CLI logs.', finished=time.monotonic())
        pool.submit(work)
        return redirect(url_for('job', job_id=job_id))

    @app.post("/demo")
    def demo():
        scenario_id = request.form.get("scenario")
        if scenario_id not in registered:
            abort(400)
        with lock:
            if any(job["status"] == "RUNNING" for job in jobs.values()):
                abort(409, "a demo is already running")
            job_id = secrets.token_hex(16)
            jobs[job_id] = {"status": "RUNNING", "runs": [], "step": "Starting isolated verification",
                            'stage': 'reproduce', 'candidate': 0, 'generator': 'curated', 'started': time.monotonic(), 'demo_step': 1}
        def work():
            try:
                directory = benchmark_root / "scenarios" / scenario_id
                for number, (mode, label) in enumerate([("fixed", "incomplete"), ("full", "incomplete"), ("full", "correct")], 1):
                    update_job(job_id, step=mode + " verification · " + label + " patch", demo_step=number)
                    report = run(directory, directory / "contract.json",
                                 (directory / "patches" / (label + ".diff")).read_text(encoding="utf-8"), store=store, mode=mode,
                                 origin='curated', progress=progress_for(job_id, number))
                    with lock:
                        jobs[job_id]["runs"].append(report["id"])
                update_job(job_id, status="COMPLETE", stage='complete', step="All three curated verifications completed", finished=time.monotonic())
            except Exception:
                app.logger.exception('isolated demo execution failed')
                update_job(job_id, status="ERROR", step="Execution failed. Inspect the CLI logs.", finished=time.monotonic())
        pool.submit(work)
        return redirect(url_for("job", job_id=job_id))

    @app.get("/jobs/<job_id>")
    def job(job_id):
        with lock:
            if job_id not in jobs:
                abort(404)
            snapshot = job_snapshot(job_id)
        return render_template("job.html", job=snapshot, job_id=job_id)

    @app.get('/api/jobs/<job_id>')
    def job_status(job_id):
        with lock:
            if job_id not in jobs:
                abort(404)
            snapshot = job_snapshot(job_id)
        return jsonify(snapshot)

    @app.get("/runs/<run_id>")
    def detail(run_id):
        try:
            report = store.load(run_id)
        except Exception:
            abort(409, "Evidence integrity could not be verified")
        if report.get('kind') == 'review':
            return render_template('review.html', report=report)
        executor = DockerExecutor()
        return render_template("detail.html", report=report, fresh=fresh(report, executor),
                               freshness_changes=freshness_changes(report, executor), summary=explanation(report), csrf=session["csrf"])

    @app.post("/runs/<run_id>/replay")
    def replay_case(run_id):
        try:
            result = replay(run_id, request.form.get("case"), store, candidate=int(request.form.get("candidate", "0")))
        except Exception as exc:
            app.logger.warning('replay denied or failed: %s', type(exc).__name__)
            return jsonify(error='Replay unavailable. Evidence may be stale or the case invalid.'), 409
        return render_template("replay.html", result=result)

    return app

