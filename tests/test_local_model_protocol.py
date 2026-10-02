import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from pratirodh.evidence import digest
from pratirodh.projects.model import LocalModel
from pratirodh.projects.budget import WorkflowBudget


@pytest.mark.parametrize('runtime', ['ollama', 'llama.cpp'])
def test_local_server_adapters_pin_and_generate(tmp_path, runtime):
    binary = tmp_path / 'runtime'
    binary.write_bytes(b'fixture-runtime')
    weights = tmp_path / 'model.gguf'
    weights.write_bytes(b'fixture-weights')
    weights_digest = 'sha256:' + digest(weights.read_bytes())
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_GET(self):
            data = {'models': [{'name': 'qwen2.5-coder:7b', 'digest': weights_digest, 'details': {'quantization_level': 'Q4_K_M'}}]} if self.path == '/api/tags' else {'status': 'ok'}
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(data).encode())
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert 'temperature' in payload or payload['options']['temperature'] == 0
            answer = json.dumps({'files': {'module.py': 'value = 2\n'}})
            data = {'response': answer, 'prompt_eval_count': 2, 'eval_count': 4} if self.path == '/api/generate' else {'choices': [{'message': {'content': answer}}], 'usage': {'total_tokens': 6}}
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(data).encode())
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = {'runtime': runtime, 'profile': 'laptop', 'endpoint': 'http://127.0.0.1:' + str(server.server_port),
                  'name': 'qwen2.5-coder:7b', 'weights_digest': weights_digest, 'runtime_digest': 'sha256:' + digest(binary.read_bytes()),
                  'runtime_binary': str(binary), 'weights_path': str(weights), 'quantization': 'Q4_K_M', 'available_memory_gb': 8}
        model = LocalModel(config)
        budget = WorkflowBudget({'seconds': 30, 'reserve_seconds': 10, 'model_calls': 8, 'candidates': 3})
        answer = model.suggest('fixture prompt', budget)
        assert answer['files']['module.py'] == 'value = 2\n'
        assert budget.model_calls == 1
        assert model.usage[0]['status'] == 'OK'
        binary.write_bytes(b'changed-runtime')
        with pytest.raises(RuntimeError):
            model.suggest('fixture prompt', budget)
        assert budget.model_calls == 2
        assert model.usage[-1]['status'] == 'ERROR'
    finally:
        server.shutdown()
        server.server_close()
