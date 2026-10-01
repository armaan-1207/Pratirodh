"""Container-only request executor. Assertions live outside the target process."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import multiprocessing


def isolated_child(job, channel):
    try:
        channel.send({'results': execute(job)})
    except Exception:
        channel.send({'error': 'target execution failed'})
    finally:
        channel.close()


def execute(job):
    with (contextlib.nullcontext(job['root']) if job.get('root') else tempfile.TemporaryDirectory()) as directory:
        root = Path(directory)
        for name, body in job["fixtures"].items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        for name, destination in job.get("symlinks", {}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(destination)
        (root / "app.py").write_text(job["source"], encoding="utf-8")
        os.chdir(root)
        os.environ.update(job.get('environment', {}))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            scope = runpy.run_path(str(root / "app.py"), run_name="pratirodh_target")
            app = scope["app"]
            app.config.update(TESTING=True)
            results = []
            for case in job["cases"]:
                try:
                    with app.test_client() as client:
                        response = client.open(case["path"], method=case.get("method", "GET"),
                                               query_string=case.get("query"),
                                               data=case.get("form"), json=case.get("json"))
                        body = response.get_data(as_text=True)
                        if len(body.encode('utf-8')) > 65536:
                            results.append({'id': case['id'], 'error': 'response exceeds evidence limit'})
                        else:
                            results.append({"id": case["id"], "status": response.status_code, "body": body})
                except Exception as exc:
                    results.append({"id": case["id"], "error": type(exc).__name__})
        return results


if __name__ == "__main__":
    job = json.load(sys.stdin)
    if "source" in job:
        try:
            print(json.dumps({"results": execute(job)}))
        except Exception as exc:
            print(json.dumps({"error": type(exc).__name__ + ": " + str(exc)[:500]}))
    else:
        outputs = []
        for source in job["sources"]:
            if job.get('version') == 2:
                # Docker runner is Linux. Preload the trusted framework before forking, so each
                # target retains a separate process without repeatedly importing Flask for every input.
                import flask
                context = multiprocessing.get_context('fork')
                results = []
                groups = [[case] for case in job['cases']]
                if not job['observed_files']:
                    # Credential profiles get isolated processes; batching requests within a profile avoids
                    # importing Flask once per request while preserving fresh configured/missing/rotated state.
                    groups = [[c for c in job['cases'] if c.get('profile', 'default') == profile]
                              for profile in job['profiles']]
                    groups = [group for group in groups if group]
                for group in groups:
                    case = group[0]
                    with tempfile.TemporaryDirectory() as root:
                        child = dict(job, source=source, cases=group, root=root,
                                     environment=job['profiles'][case.get('profile', 'default')])
                        child.pop('sources')
                        receiver, sender = context.Pipe(duplex=False)
                        process = context.Process(target=isolated_child, args=(child, sender))
                        try:
                            process.start()
                            sender.close()
                            if not receiver.poll(10):
                                raise TimeoutError('target timeout')
                            group_results = receiver.recv()['results']
                            process.join(timeout=1)
                            if process.is_alive():
                                raise TimeoutError('target did not exit')
                            if len(group_results) != len(group):
                                raise ValueError('missing target results')
                            # Supervisor observes effects after target process exits; target cannot supply these fields.
                            for result in group_results:
                                result['files'] = {name: (Path(root) / name).exists() for name in job['observed_files']}
                        except (TimeoutError, EOFError, ValueError, KeyError, IndexError):
                            group_results = [{'id': c['id'], 'error': 'target timeout or invalid output'} for c in group]
                        finally:
                            if process.is_alive():
                                process.kill()
                                process.join(timeout=1)
                            receiver.close()
                        results.extend(group_results)
                by_id = {r['id']: r for r in results}
                results = [by_id[c['id']] for c in job['cases']]
                outputs.append({'results': results})
                continue
            child = dict(job, source=source)
            child.pop("sources")
            try:
                process = subprocess.run([sys.executable, "-B", __file__], input=json.dumps(child),
                                         text=True, capture_output=True, timeout=15)
                outputs.append(json.loads(process.stdout) if process.returncode == 0 else
                               {"error": "target process failed"})
            except (subprocess.TimeoutExpired, ValueError):
                outputs.append({"error": "target timeout or invalid executor output"})
        print(json.dumps(outputs))

