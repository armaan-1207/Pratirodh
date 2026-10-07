# Local deployment checks — 7 October 2026

`tools/verify_local_deployment.py` exercises an isolated staging dashboard and
local Caddy proxy using already installed Docker images. It does not provision
public infrastructure, read operator credentials or use the live evidence store.
Public deployment is deferred at the operator's request.

The corrected local check verified a trusted local CA and hostname, rejection
without that CA, anonymous HTTP 401, authenticated HTTP 200, read-only POST 403,
unexpected-host rejection at both proxy and backend (403), secure cookies,
HSTS/CSP headers, loopback-only proxy exposure and no published backend ports.
The proxy's explicit fallback prevents an unmatched hostname from receiving an
empty successful response. The verifier refuses optimized Python, which would
otherwise disable its assertions.

Synthetic signed evidence survived a staging backup and restore with its trust
anchor; the public snapshot excluded the private key. Tampered restored evidence
was rejected. A temporary local log collector delivered one sanitized alert
after five integrity denials to a local HTTP receiver. These checks do not verify
an operator's backup infrastructure, retention policy or external alert service.

The first staging receipt accepted an empty proxy HTTP 200 for an unmatched host.
That result is superseded by the strict host-rejection check. Existing receipts
remain in ignored local evidence; successful verification now requires HTTP 403
for that request. No security requirement was removed to obtain a pass.

Run in a development environment with the dashboard candidate and `caddy:2`
already present:

```powershell
python tools/verify_local_deployment.py --image pratirodh-dashboard:cleanup-candidate --output run_output/local-deployment-new.json
```

Choose a new receipt path each time. Temporary containers and their network are
removed after the check. Signing keys, transient credentials and generated
receipts are excluded from release files. A local pass does not establish public
TLS, external delivery, host patching, sustained load or disaster recovery.
