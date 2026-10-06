"""Attest the Azure model over SSH without exposing its HTTP endpoint."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

RUNTIME = 'sha256:0b0650a962dda61ec0598141ea11e3b688d225e926c9c00bc2c299d0ed34c4f8'
WEIGHTS = 'sha256:dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364'
REMOTE = r'''
import hashlib,json,time,urllib.request
from pathlib import Path
def get(path,payload=None):
    request=urllib.request.Request('http://127.0.0.1:11434'+path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request,timeout=180) as response:
        return json.load(response)
available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))/1024/1024
model=next(m for m in get('/api/tags')['models'] if m['name']=='qwen2.5-coder:7b')
runtime='sha256:'+hashlib.sha256(Path('/usr/local/bin/ollama').read_bytes()).hexdigest()
weights='sha256:'+model['digest'].removeprefix('sha256:')
if runtime!=EXPECTED_RUNTIME or weights!=EXPECTED_WEIGHTS:
    raise ValueError('runtime/model pin mismatch')
if model['details']['quantization_level']!='Q4_K_M' or available<8:
    raise ValueError('quantization/memory preflight failed')
started=time.monotonic()
response=get('/api/generate',{'model':model['name'],'prompt':'Return the JSON object {"ok":true}.',
    'stream':False,'format':'json','options':{'num_ctx':8192,'num_predict':64,'temperature':0}})
if json.loads(response['response']).get('ok') is not True:
    raise ValueError('inference response failed')
print(json.dumps({'status':'PASS','role':'model','runtime':'ollama','model':model['name'],
    'runtime_version':get('/api/version')['version'],'runtime_digest':runtime,'weights_digest':weights,
    'quantization':model['details']['quantization_level'],'available_memory_gib':available,
    'elapsed_seconds':time.monotonic()-started,'prompt_tokens':response.get('prompt_eval_count'),
    'completion_tokens':response.get('eval_count'),'inference_validated':True,
    'boot_id_digest':hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes().strip()).hexdigest(),
    'machine_id_digest':hashlib.sha256(Path('/etc/machine-id').read_bytes().strip()).hexdigest()}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='pratirodh-model')
    parser.add_argument('--output', type=Path, default=Path('run_output/upstream-validation/model-preflight.json'))
    args = parser.parse_args()
    script = 'EXPECTED_RUNTIME=' + repr(RUNTIME) + '\nEXPECTED_WEIGHTS=' + repr(WEIGHTS) + '\n' + REMOTE
    try:
        process = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=10', args.host, 'python3 -'], input=script,
            capture_output=True, text=True, encoding='utf-8', timeout=210, check=True)
        result = json.loads(process.stdout)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result = {'status': 'BLOCKED', 'role': 'model', 'error': type(error).__name__}
        if isinstance(error, subprocess.CalledProcessError):
            result['detail'] = error.stderr[-2000:]
    result.update(host=args.host, observed_at=datetime.now(timezone.utc).isoformat())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
