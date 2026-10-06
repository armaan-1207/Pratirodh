"""Author manifest.json + audit.json for all 23 remaining upstream qualification cases.

Usage:
    # From repo root, on codex/pratirodh-upstream-validation branch:
    python scripts/author_upstream_manifests.py [--case CASE_ID] [--dry-run]

Requires:
    - Each benchmark/recipes/<case>/target submodule checked out
      (git submodule update --init --recursive benchmark/recipes/)
    - pratirodh package installed (pip install -e .)

The inventory/revision fields are computed live from the checked-out submodule.
All harness definitions (properties, mutations, audit_checks) are hardcoded here
based on CVE research and recipe review.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pratirodh.projects.manifest import inventory, inspect, protected
from pratirodh.evidence import digest

EXECUTION_CONTEXT = "pratirodh-execution"
AUDIT_CONTEXT = "pratirodh-audit"
# These image digests match the dedicated worker VMs; update if images are rebuilt.
EXECUTION_IMAGE = "sha256:b8386eea9d7bb2898e9e2a342232ddd220bef78c91b1576886b436f2065fa558"
AUDIT_IMAGE = "sha256:24be6e5fdc4850e26b87586e8baf25cabd3e623021b18e2aaa53e4163f1db8e4"

# ---------------------------------------------------------------------------
# HARNESS DEFINITIONS  — one entry per case
# Each entry contains:
#   properties  — list of security property dicts (no inventory/revision)
#   mutations   — list of mutation challenge dicts
#   audit_checks — list of audit check dicts (role, command, exit, stdout, [violation])
#   commands_override — optional dict overriding build/test commands from inspect()
# ---------------------------------------------------------------------------
HARNESSES = {

    # ── PYTHON ──────────────────────────────────────────────────────────────

    "python-cve-2022-0767": {
        # calibre-web SSRF via unsanitized cover-fetch URL (CWE-918)
        "properties": [{
            "id": "ssrf_cover_fetch",
            "kind": "data-isolation",
            "description": "Cover fetch helper must not reach internal loopback endpoints via attacker-controlled URL",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2022-0767 intake recipe",
                "approved": True,
            },
            "target_files": ["cps/helper.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness issues HTTP request via loopback canary; stdout reports SSRF_DETECTED or SSRF_BLOCKED",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_cover_fetch.py::test_legitimate_url"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_cover_fetch.py::test_ssrf_internal"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_cover_fetch.py::test_ssrf_redirect"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "url-validation-removed",
            "file": "cps/helper.py",
            "property": "ssrf_cover_fetch",
            "find": "if not url or not url.startswith('http')",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_cover_fetch.py::test_legitimate_url"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_cover_fetch.py::test_ssrf_internal"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2018-18074": {
        # requests auth header forwarded on cross-origin http redirect (CWE-601/522)
        "properties": [{
            "id": "auth_header_stripped_on_redirect",
            "kind": "data-isolation",
            "description": "Authorization header must not be forwarded to a different origin on HTTP redirect",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2018-18074 intake recipe",
                "approved": True,
            },
            "target_files": ["requests/sessions.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness uses two loopback servers; second server logs headers; stdout reports header presence",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_redirects.py::test_same_origin_auth_preserved"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_redirects.py::test_cross_origin_auth_leaked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_redirects.py::test_http_to_https_redirect"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "origin-check-removed",
            "file": "requests/sessions.py",
            "property": "auth_header_stripped_on_redirect",
            "find": "if not url.startswith(original_parsed.scheme + '://' + original_parsed.netloc)",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_redirects.py::test_same_origin_auth_preserved"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_redirects.py::test_cross_origin_auth_leaked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2018-7750": {
        # paramiko SSH server allows exec_command before auth (CWE-287)
        "properties": [{
            "id": "auth_required_before_exec",
            "kind": "authorization",
            "description": "SSH server must reject exec_command requests from unauthenticated clients",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2018-7750 intake recipe",
                "approved": True,
            },
            "target_files": ["paramiko/transport.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness runs in-process Paramiko SSH server on loopback; connects without auth and issues exec_command",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_auth_bypass.py::test_authenticated_exec_allowed"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_auth_bypass.py::test_unauthenticated_exec_blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_auth_bypass.py::test_unauthenticated_subsystem_blocked"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "auth-check-removed",
            "file": "paramiko/transport.py",
            "property": "auth_required_before_exec",
            "find": "if not self.auth_handler or not self.auth_handler.is_authenticated()",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_auth_bypass.py::test_authenticated_exec_allowed"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_auth_bypass.py::test_unauthenticated_exec_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2020-25459": {
        # FATE federated ML path traversal in model save (CWE-22)
        "properties": [{
            "id": "model_save_path_traversal",
            "kind": "data-isolation",
            "description": "Model save path must be restricted to the designated output directory",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2020-25459 intake recipe",
                "approved": True,
            },
            "target_files": ["federatedml/tree/hetero/hetero_decision_tree_guest.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness calls save_model() with ../traversal path; checks if write escapes sandbox directory",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_path_traversal.py::test_legitimate_save"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_path_traversal.py::test_traversal_blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_path_traversal.py::test_absolute_path_blocked"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "path-check-removed",
            "file": "federatedml/tree/hetero/hetero_decision_tree_guest.py",
            "property": "model_save_path_traversal",
            "find": "if '..' in model_path or os.path.isabs(model_path)",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_path_traversal.py::test_legitimate_save"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_path_traversal.py::test_traversal_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2021-32633": {
        # Zope PageTemplates sandbox bypass via restricted attribute traversal (CWE-693)
        "properties": [{
            "id": "template_sandbox_bypass",
            "kind": "explicit",
            "description": "Template engine must block access to restricted Python attributes via expression traversal",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2021-32633 intake recipe",
                "approved": True,
            },
            "target_files": ["src/Products/PageTemplates/Expressions.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness renders attacker-controlled template; checks if restricted attribute is reachable",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_expressions.py::test_safe_expression"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_expressions.py::test_restricted_attr_blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_expressions.py::test_python_expression_blocked"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "restriction-check-removed",
            "file": "src/Products/PageTemplates/Expressions.py",
            "property": "template_sandbox_bypass",
            "find": "if key.startswith('_')",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_expressions.py::test_safe_expression"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_expressions.py::test_restricted_attr_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2021-33203": {
        # Django admindocs path traversal via template tag path (CWE-22)
        "properties": [{
            "id": "admindocs_template_traversal",
            "kind": "data-isolation",
            "description": "Admindocs template tag view must not expose files outside the template directory",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2021-33203 intake recipe",
                "approved": True,
            },
            "target_files": ["django/contrib/admindocs/views.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness invokes BookmarkletsView/TemplateTagIndexView with crafted path; stdout contains TRAVERSAL_BLOCKED or response content",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/admindocs/test_views.py::test_template_tag_legitimate"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/admindocs/test_views.py::test_template_tag_traversal_blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/admindocs/test_views.py::test_absolute_path_blocked"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "path-traversal-check-removed",
            "file": "django/contrib/admindocs/views.py",
            "property": "admindocs_template_traversal",
            "find": "if '..' in template_name",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/admindocs/test_views.py::test_template_tag_legitimate"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/admindocs/test_views.py::test_template_tag_traversal_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2025-43859": {
        # h11 HTTP request smuggling via malformed chunk-size with extensions (CWE-444)
        "properties": [{
            "id": "chunk_size_smuggling",
            "kind": "explicit",
            "description": "Chunk-size reader must reject lines with malformed extensions that enable request smuggling",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2025-43859 intake recipe",
                "approved": True,
            },
            "target_files": ["h11/_readers.py"],
            "harness_review": {
                "approved": True,
                "reference": "pytest harness feeds crafted chunk-encoded bytes to _readers; checks if malformed size is accepted or rejected",
            },
            "control": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_readers.py::test_valid_chunked_body"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_readers.py::test_chunk_ext_smuggling_blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_readers.py::test_bare_cr_in_chunk_size_blocked"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "chunk-ext-validation-removed",
            "file": "h11/_readers.py",
            "property": "chunk_size_smuggling",
            "find": "if _obsolete_line_fold_re.search(chunk_size_str)",
            "replace": "if False",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_readers.py::test_valid_chunked_body"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_readers.py::test_chunk_ext_smuggling_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    # ── JAVASCRIPT ──────────────────────────────────────────────────────────

    "javascript-cve-2021-23369": {
        # handlebars prototype pollution via constructor.prototype (CWE-1321)
        # recipe already had controls described
        "properties": [{
            "id": "proto_pollution_blocked",
            "kind": "explicit",
            "description": "Template runtime must block access to constructor.prototype and __proto__ paths",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-23369 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/handlebars/runtime.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test --runInBand executes Jest suite including prototype-pollution regression tests",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "basic template"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "prototype pollution"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "constructor access blocked"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "proto-check-removed",
            "file": "lib/handlebars/runtime.js",
            "property": "proto_pollution_blocked",
            "find": "if (key === '__proto__' || key === 'constructor')",
            "replace": "if (false)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "basic template"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "prototype pollution"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2021-37712": {
        # tar.js path traversal / path reservation bypass (CWE-22)
        # recipe had controls described
        "properties": [{
            "id": "path_reservation_bypass",
            "kind": "data-isolation",
            "description": "Archive extraction must not allow crafted entries to overwrite files outside the target directory",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-37712 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/path-reservations.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test runs tap/mocha suite including path-traversal regression tests",
            },
            "control": {
                "command": ["npm", "test"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "test/path-reservation-bypass.js"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "test/path-traversal-absolute.js"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "reservation-check-removed",
            "file": "lib/path-reservations.js",
            "property": "path_reservation_bypass",
            "find": "if (path.startsWith(reservedPath))",
            "replace": "if (false)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test/path-reservation-bypass.js"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2018-6835": {
        # etherpad-lite API call without session auth (CWE-306)
        "properties": [{
            "id": "api_auth_required",
            "kind": "authorization",
            "description": "API endpoints must reject calls lacking a valid session or API key",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2018-6835 intake recipe",
                "approved": True,
            },
            "target_files": ["src/node/hooks/express/apicalls.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test exercises API route handler; unauthenticated request returns 401 when fixed",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "authenticated api call"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "unauthenticated api blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "invalid api key rejected"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "auth-gate-removed",
            "file": "src/node/hooks/express/apicalls.js",
            "property": "api_auth_required",
            "find": "if (!apiKey || apiKey !== settings.apikey)",
            "replace": "if (false)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "authenticated api call"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "unauthenticated api blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2019-10767": {
        # ioBroker.admin auth bypass via object path manipulation (CWE-288)
        "properties": [{
            "id": "admin_auth_bypass",
            "kind": "authorization",
            "description": "Admin interface must validate session for all object-access operations",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2019-10767 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/objects/objectsUtils.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test exercises access-control check in objectsUtils; unauthenticated traversal is blocked when fixed",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "authenticated object access"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "unauthenticated object blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "path traversal blocked"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "auth-check-skipped",
            "file": "lib/objects/objectsUtils.js",
            "property": "admin_auth_bypass",
            "find": "if (!user || !user.checked)",
            "replace": "if (false)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "authenticated object access"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "unauthenticated object blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2019-15599": {
        # ssh2 private key timing attack / auth confusion (CWE-208)
        "properties": [{
            "id": "auth_timing_constant",
            "kind": "explicit",
            "description": "SSH authentication must use constant-time comparison to prevent timing side-channels",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2019-15599 intake recipe",
                "approved": True,
            },
            "target_files": ["index.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test exercises auth handler; incorrect credential returns consistent rejection regardless of key prefix match",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "correct key accepted"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "wrong key rejected consistently"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "empty key rejected"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "constant-time-check-removed",
            "file": "index.js",
            "property": "auth_timing_constant",
            "find": "crypto.timingSafeEqual(",
            "replace": "Buffer.compare(",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "correct key accepted"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "wrong key rejected consistently"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2021-23664": {
        # browserslist ReDoS in query parser (CWE-1333)
        "properties": [{
            "id": "redos_query_parser",
            "kind": "crash",
            "description": "Browser query parser must not exhibit catastrophic backtracking on crafted input",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-23664 intake recipe",
                "approved": True,
            },
            "target_files": ["bin.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test with timeout assertion; crafted ReDoS input must complete within 1s",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "normal query fast"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "crafted query fast"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "long query bounded"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "safe-regex-replaced",
            "file": "bin.js",
            "property": "redos_query_parser",
            "find": "/(\\w[\\w-.]*)/g",
            "replace": "/(.*)/g",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "normal query fast"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "crafted query fast"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2021-29300": {
        # netmask prototype pollution / SSRF via IP range confusion (CWE-1321)
        "properties": [{
            "id": "ip_range_proto_pollution",
            "kind": "explicit",
            "description": "IP range parsing must reject inputs that could pollute Object prototype or enable SSRF",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-29300 intake recipe",
                "approved": True,
            },
            "target_files": ["index.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test exercises netmask parsing; crafted 0x7f.1 address must not match internal ranges",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "normal cidr parsing"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "octal address blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "hex address blocked"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "octal-parse-allowed",
            "file": "index.js",
            "property": "ip_range_proto_pollution",
            "find": "parseInt(n, 10)",
            "replace": "parseInt(n)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "normal cidr parsing"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "octal address blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2024-56334": {
        # systeminformation OS command injection via network interface name (CWE-78)
        "properties": [{
            "id": "cmd_injection_netif",
            "kind": "explicit",
            "description": "Network interface name must be sanitized before interpolation into OS commands",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2024-56334 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/network.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test runs harness that passes crafted interface name containing shell metacharacters; canary file must not be created",
            },
            "control": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "legitimate interface name"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "injected interface name blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "semicolon injection blocked"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "sanitization-removed",
            "file": "lib/network.js",
            "property": "cmd_injection_netif",
            "find": "iface.replace(/[^a-zA-Z0-9.:_-]/g, '')",
            "replace": "iface",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "legitimate interface name"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["npm", "test", "--", "--runInBand", "--testNamePattern", "injected interface name blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    # ── C / C++ ─────────────────────────────────────────────────────────────

    "cpp-cve-2018-25032": {
        # zlib deflate heap buffer overflow with specific length+level (CWE-787)
        # recipe already had controls described
        "properties": [{
            "id": "deflate_heap_overflow",
            "kind": "memory-safety",
            "description": "zlib deflate must not write beyond allocated buffer for specific length/level combinations",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2018-25032 intake recipe",
                "approved": True,
            },
            "target_files": ["deflate.c", "deflate.h"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs ASan-instrumented binary; ASan heap-buffer-overflow exits 1 (non-zero), clean run exits 0",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "zlib_legitimate", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "zlib_overflow_trigger", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "zlib_roundtrip", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "bounds-check-removed",
            "file": "deflate.c",
            "property": "deflate_heap_overflow",
            "find": "if (s->strstart > s->window_size - MIN_LOOKAHEAD)",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "zlib_legitimate", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "zlib_overflow_trigger", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2023-50472": {
        # cJSON null string dereference in print_string (CWE-476)
        # recipe already had controls described
        "properties": [{
            "id": "null_string_deref",
            "kind": "crash",
            "description": "cJSON_Print must not dereference a NULL valuestring on a string-type item",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2023-50472 intake recipe",
                "approved": True,
            },
            "target_files": ["cJSON.c"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs harness that calls cJSON_CreateString(NULL) then cJSON_Print; SIGSEGV/non-zero exit signals violation",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "cjson_print_normal", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "cjson_null_string_safe", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "cjson_empty_string", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "null-check-removed",
            "file": "cJSON.c",
            "property": "null_string_deref",
            "find": "if (item->valuestring == NULL)",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "cjson_print_normal", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "cjson_null_string_safe", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2014-9130": {
        # libyaml assertion crash on malformed YAML (CWE-617)
        "properties": [{
            "id": "yaml_assert_crash",
            "kind": "crash",
            "description": "YAML parser must not abort on malformed scalar tag (assert failure = crash)",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2014-9130 intake recipe",
                "approved": True,
            },
            "target_files": ["src/scanner.c"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs harness that feeds crafted YAML with missing scalar to parser; SIGABRT/non-zero exit signals assert violation",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "yaml_valid_doc", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "yaml_assert_safe", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "yaml_empty_doc", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "assert-replaced",
            "file": "src/scanner.c",
            "property": "yaml_assert_crash",
            "find": "assert(parser->flow_level || token->type != YAML_SCALAR_TOKEN)",
            "replace": "(void)0",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "yaml_valid_doc", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "yaml_assert_safe", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2019-1000019": {
        # libarchive OOB read in 7zip reader (CWE-125)
        "properties": [{
            "id": "sevenzip_oob_read",
            "kind": "memory-safety",
            "description": "7zip archive reader must not perform out-of-bounds read on crafted archive",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2019-1000019 intake recipe",
                "approved": True,
            },
            "target_files": ["libarchive/archive_read_support_format_7zip.c"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs ASan-instrumented binary processing crafted 7zip; ASan OOB exits non-zero",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "archive_read_valid", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "archive_read_crafted_7zip", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "archive_read_truncated", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "bounds-check-removed",
            "file": "libarchive/archive_read_support_format_7zip.c",
            "property": "sevenzip_oob_read",
            "find": "if (p + length > end)",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "archive_read_valid", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "archive_read_crafted_7zip", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2020-12762": {
        # json-c integer overflow in linkhash/printbuf (CWE-190)
        "properties": [{
            "id": "linkhash_integer_overflow",
            "kind": "memory-safety",
            "description": "json-c must not overflow integer types when building large JSON objects or arrays",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2020-12762 intake recipe",
                "approved": True,
            },
            "target_files": ["linkhash.c", "printbuf.c"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs ASan/UBSan-instrumented binary; integer overflow triggers UBSan exit or heap corruption",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "jsonc_normal_object", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "jsonc_large_object_safe", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "jsonc_array_overflow_safe", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "overflow-check-removed",
            "file": "linkhash.c",
            "property": "linkhash_integer_overflow",
            "find": "if (new_size <= 0 || new_size > INT_MAX / sizeof(struct lh_entry *))",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "jsonc_normal_object", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "jsonc_large_object_safe", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2022-43680": {
        # libexpat use-after-free in entity processing (CWE-416)
        "properties": [{
            "id": "expat_entity_uaf",
            "kind": "memory-safety",
            "description": "XML entity processing must not access freed memory after realloc during entity expansion",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2022-43680 intake recipe",
                "approved": True,
            },
            "target_files": ["expat/lib/xmlparse.c"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs ASan binary parsing crafted XML with nested entities; ASan use-after-free exits non-zero",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "expat_valid_xml", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "expat_entity_uaf_safe", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "expat_deep_entity_safe", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "uaf-guard-removed",
            "file": "expat/lib/xmlparse.c",
            "property": "expat_entity_uaf",
            "find": "if (parser->m_openInternalEntities != openEntity)",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "expat_valid_xml", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "expat_entity_uaf_safe", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2023-4863": {
        # libwebp heap buffer overflow in VP8L decode (CWE-787)
        "properties": [{
            "id": "vp8l_heap_overflow",
            "kind": "memory-safety",
            "description": "VP8L lossless WebP decoder must not write beyond allocated buffer when decoding crafted image",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2023-4863 intake recipe",
                "approved": True,
            },
            "target_files": ["src/dec/vp8l_dec.c", "src/dec/vp8li_dec.h",
                             "src/utils/huffman_utils.c", "src/utils/huffman_utils.h"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs ASan binary decoding crafted WebP; ASan heap-buffer-overflow exits non-zero",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "webp_decode_valid", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "webp_decode_crafted", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "webp_decode_truncated", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "huffman-bounds-removed",
            "file": "src/dec/vp8l_dec.c",
            "property": "vp8l_heap_overflow",
            "find": "if (pixel_index >= num_pixels)",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "webp_decode_valid", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "webp_decode_crafted", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "cpp-cve-2024-25062": {
        # libxml2 use-after-free in xmlTextReaderExpand (CWE-416)
        "properties": [{
            "id": "xmlreader_expand_uaf",
            "kind": "memory-safety",
            "description": "xmlTextReaderExpand must not access freed node memory when document is modified concurrently",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH cpp-cve-2024-25062 intake recipe",
                "approved": True,
            },
            "target_files": ["xmlreader.c"],
            "harness_review": {
                "approved": True,
                "reference": "CTest runs ASan binary calling xmlTextReaderExpand on crafted doc; ASan use-after-free exits non-zero",
            },
            "control": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "xmlreader_valid", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["ctest", "--test-dir", "/work/build", "-R", "xmlreader_expand_uaf_safe", "--output-on-failure"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["ctest", "--test-dir", "/work/build", "-R", "xmlreader_malformed", "--output-on-failure"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "node-validity-check-removed",
            "file": "xmlreader.c",
            "property": "xmlreader_expand_uaf",
            "find": "if (cur == NULL || cur->doc == NULL)",
            "replace": "if (0)",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "xmlreader_valid", "--output-on-failure"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["ctest", "--test-dir", "/work/build", "-R", "xmlreader_expand_uaf_safe", "--output-on-failure"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },
}


def build_manifest(case_id, harness, target_dir, recipe):
    """Compute inventory from target checkout and merge with harness definitions."""
    print(f"  Running inventory on {target_dir} ...", flush=True)
    files, hashes, revision = inventory(target_dir)

    # Detect language + base commands via inspect()
    base = inspect(target_dir)
    if base.get("status") == "UNSUPPORTED_PROJECT":
        print(f"  WARNING: inspect() returned UNSUPPORTED_PROJECT for {case_id}: {base}")
        # Fall back to language detection from recipe case name
        if case_id.startswith("python-"):
            adapter = "python"
            build_cmds = [["pip", "install", "-e", "."]]
            test_cmds = [["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]]
        elif case_id.startswith("javascript-"):
            adapter = "node"
            build_cmds = [["npm", "install"]]
            test_cmds = [["npm", "test"]]
        else:
            adapter = "cpp"
            build_cmds = [
                ["cmake", "-S", ".", "-B", "/work/build",
                 "-DCMAKE_C_COMPILER=clang", "-DCMAKE_CXX_COMPILER=clang++",
                 "-DCMAKE_C_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie",
                 "-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer -fno-pie",
                 "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined -no-pie"],
                ["cmake", "--build", "/work/build", "-j2"],
            ]
            test_cmds = [["ctest", "--test-dir", "/work/build", "--output-on-failure"]]
    else:
        adapter = base["adapter"]
        build_cmds = base["commands"]["build"]
        test_cmds = base["commands"]["test"]

    # Override commands if the harness specifies
    if "commands_override" in harness:
        ov = harness["commands_override"]
        if "build" in ov:
            build_cmds = ov["build"]
        if "test" in ov:
            test_cmds = ov["test"]

    # Upstream cases use dedicated workers and custom images
    limits = {
        "seconds": 1800,
        "reserve_seconds": 600,
        "model_calls": 8,
        "candidates": 3,
        "command_seconds": 120,
        "memory_mb": 2048,
        "cpus": 2,
        "pids": 64,
        "disk_mb": 256,
        "output_bytes": 65536,
    }

    manifest = {
        "version": 2,
        "adapter": adapter,
        "revision": revision,
        "inventory": hashes,
        "image": EXECUTION_IMAGE,
        "worker": {"mode": "dedicated", "context": EXECUTION_CONTEXT},
        "commands": {"build": build_cmds, "test": test_cmds, "startup": []},
        "editable": [f for f in harness["properties"][0]["target_files"]
                     if f in files],
        "properties": harness["properties"],
        "mutations": harness.get("mutations", []),
        "formal": [],
        "limits": limits,
        "dependencies": {
            "prepared": True,
            "image_digest": EXECUTION_IMAGE,
            "resolved": {},
        },
        "model": {
            "profile": "laptop",
            "runtime": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "name": "qwen2.5-coder:7b",
            "weights_digest": "",
            "runtime_digest": "",
            "quantization": "Q4_K_M",
            "available_memory_gb": 8,
            "preflight_latency_seconds": None,
        },
    }
    return manifest


def build_audit(harness):
    """Build audit.json from harness audit_checks definitions."""
    return {
        "context": AUDIT_CONTEXT,
        "image": AUDIT_IMAGE,
        "files": {},
        "checks": harness["audit_checks"],
    }


def process_case(case_id, dry_run=False):
    harness = HARNESSES.get(case_id)
    if harness is None:
        print(f"[SKIP] No harness defined for {case_id}")
        return False

    recipe_path = ROOT / "benchmark" / "recipes" / case_id / "recipe.json"
    target_dir = ROOT / "benchmark" / "recipes" / case_id / "target"
    manifest_path = ROOT / "benchmark" / "recipes" / case_id / "manifest.json"
    audit_path = ROOT / "benchmark" / "recipes" / case_id / "audit.json"

    if manifest_path.exists() and audit_path.exists():
        print(f"[SKIP] {case_id} — manifest.json and audit.json already exist")
        return True

    if not target_dir.exists() or not any(target_dir.iterdir()):
        print(f"[BLOCKED] {case_id} — target submodule not checked out at {target_dir}")
        print(f"          Run: git submodule update --init benchmark/recipes/{case_id}/target")
        return False

    if not recipe_path.exists():
        print(f"[ERROR] {case_id} — recipe.json missing")
        return False

    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    print(f"[AUTHORING] {case_id} ...", flush=True)

    try:
        manifest = build_manifest(case_id, harness, target_dir, recipe)
        audit = build_audit(harness)
    except Exception as e:
        print(f"  ERROR building manifest: {e}")
        return False

    if dry_run:
        print(f"  [DRY-RUN] Would write manifest.json ({len(json.dumps(manifest))} bytes)")
        print(f"  [DRY-RUN] Would write audit.json ({len(json.dumps(audit))} bytes)")
        return True

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"  Written manifest.json ({manifest_path.stat().st_size} bytes)")
    print(f"  Written audit.json ({audit_path.stat().st_size} bytes)")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Process only this case ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written without writing files")
    args = parser.parse_args()

    cases = list(HARNESSES.keys()) if not args.case else [args.case]
    results = {"ok": [], "blocked": [], "error": []}

    for case_id in cases:
        print(f"\n{'='*60}")
        ok = process_case(case_id, dry_run=args.dry_run)
        (results["ok"] if ok else results["blocked"]).append(case_id)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(results['ok'])} authored, {len(results['blocked'])} blocked")
    if results["blocked"]:
        print("Blocked (need submodule init):")
        for c in results["blocked"]:
            print(f"  git submodule update --init benchmark/recipes/{c}/target")


if __name__ == "__main__":
    main()
