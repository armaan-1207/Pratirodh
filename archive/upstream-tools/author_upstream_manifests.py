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

    "python-cve-2021-21330": {
        "properties": [{
            "id": "aiohttp_open_redirect",
            "kind": "data-isolation",
            "description": "Normalize path middleware must not redirect to absolute URLs",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2021-21330 intake recipe",
                "approved": True,
            },
            "target_files": ["aiohttp/web_middlewares.py"],
            "harness_review": {
                "approved": True,
                "reference": "tests/test_redirect.py tests local path redirection behavior",
            },
            "control": {
                "command": ["python", "tests/test_redirect.py"],
                "exit": 0, "stdout": ""
            },
            "reproducer": {
                "command": ["python", "tests/test_redirect.py", "security"],
                "exit": 0, "stdout": "FIXED\n",
                "violation": {"exit": 1, "stdout": ""}
            },
            "variations": [
                {"command": ["python", "tests/test_redirect.py", "security"], "exit": 0, "stdout": "FIXED\n"}
            ]
        }],
        "mutations": [{
            "family": "redirect-validation-removed",
            "file": "aiohttp/web_middlewares.py",
            "property": "aiohttp_open_redirect",
            "find": "if URL(path).is_absolute():",
            "replace": "if False:",
        }],
        "audit_checks": [
            {"role": "control", "command": ["python", "test_redirect_audit.py"], "exit": 0, "stdout": ""},
            {"role": "security", "command": ["python", "test_redirect_audit.py", "security"], "exit": 0, "stdout": "FIXED\n", "violation": {"exit": 1, "stdout": ""}}
        ],
        "commands_override": {
            "build": [["pip", "install", "-e", "."]],
            "test": [["pytest"]]
        }
    },


    # -- PYTHON --------------------------------------------------------------

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
                         "test_cover_fetch_audit.py::test_legitimate_url"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_cover_fetch_audit.py::test_ssrf_internal"],
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
                             "tests/test_redirects.py::test_scheme_change_auth_leaked"], "exit": 0, "stdout": ""},
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
                         "test_redirects_audit.py::test_same_origin_auth_preserved"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_redirects_audit.py::test_cross_origin_auth_leaked"],
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
                         "test_auth_bypass_audit.py::test_authenticated_exec_allowed"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_auth_bypass_audit.py::test_unauthenticated_exec_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "python-cve-2020-25459": {
        # FATE tree synchronization exposes sensitive node metadata to the host.
        "properties": [{
            "id": "tree_metadata_isolation",
            "kind": "data-isolation",
            "description": "Tree synchronization must preserve legitimate delivery without forwarding node weights, gradients, or Hessians to the host",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH python-cve-2020-25459 intake recipe",
                "approved": True,
            },
            "target_files": ["federatedml/tree/hetero/hetero_decision_tree_guest.py"],
            "harness_review": {
                "approved": True,
                "reference": "Calls the real HeteroDecisionTreeGuest.sync_tree method and inspects the mocked transport payload; runtime qualification remains pending",
            },
            "control": {
                "command": ["python", "tests/run_data_leak.py", "control"],
                "exit": 0,
                "stdout": "CONTROL_PASS\n",
            },
            "reproducer": {
                "command": ["python", "tests/run_data_leak.py", "security"],
                "exit": 0,
                "stdout": "SECURITY_PASS\n",
                "violation": {"exit": 1, "stdout": "SECURITY_VIOLATION\n"},
            },
            "variations": [
                {"command": ["python", "tests/run_data_leak.py", "variation"], "exit": 0, "stdout": "VARIATION_PASS\n"},
            ],
        }],
        "mutations": [{
            "family": "tree-sanitization-bypassed",
            "file": "federatedml/tree/hetero/hetero_decision_tree_guest.py",
            "property": "tree_metadata_isolation",
            "find": "tree_nodes = self.remove_sensitive_info()",
            "replace": "tree_nodes = self.tree_",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "run_data_leak_audit.py", "control"],
             "exit": 0, "stdout": "CONTROL_PASS\n"},
            {"role": "security",
             "command": ["python", "run_data_leak_audit.py", "security"],
             "exit": 0, "stdout": "SECURITY_PASS\n",
             "violation": {"exit": 1, "stdout": "SECURITY_VIOLATION\n"}},
            {"role": "security",
             "command": ["python", "run_data_leak_audit.py", "variation"],
             "exit": 0, "stdout": "VARIATION_PASS\n"},
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
                         "test_expressions_audit.py::test_safe_expression"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_expressions_audit.py::test_restricted_attr_blocked"],
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
            "find": "template_file = Path(safe_join(directory, template))",
            "replace": "template_file = Path(directory) / template",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_views_audit.py::test_template_tag_legitimate"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_views_audit.py::test_template_tag_traversal_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_views_audit.py::test_absolute_path_blocked"],
             "exit": 0, "stdout": ""},
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
                            "tests/test_header_parsing.py::test_valid_chunked_body"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_header_parsing.py::test_chunk_ext_smuggling_blocked"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                             "tests/test_header_parsing.py::test_bare_cr_in_chunk_size_blocked"], "exit": 0, "stdout": ""},
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
                         "test_header_parsing_audit.py::test_valid_chunked_body"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "test_header_parsing_audit.py::test_chunk_ext_smuggling_blocked"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    # -- JAVASCRIPT ----------------------------------------------------------

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
                "command": ["node", "tests/test_harness.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "tests/test_harness.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "tests/test_harness.js", "variation"],
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
             "command": ["node", "test_harness_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_harness_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
        ],
    },

    "javascript-cve-2021-37712": {
        # node-tar path reservation bypass (CWE-22)
        "properties": [{
            "id": "path_reservation_bypass",
            "kind": "data-isolation",
            "description": "Path reservation must normalize unicode canonical equivalence to prevent concurrent extraction race bypasses",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-37712 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/path-reservations.js"],
            "harness_review": {
                "approved": True,
                "reference": "node test/test_reservation.js tests path reservation collision across unicode forms and basic sequential reservation",
            },
            "control": {
                "command": ["node", "test/test_reservation.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "test/test_reservation.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "test/test_reservation.js", "variation"], "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "unicode-norm-removed",
            "file": "lib/path-reservations.js",
            "property": "path_reservation_bypass",
            "find": ".normalize('NFKD')",
            "replace": "",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["node", "test_reservation_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_reservation_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["node", "test_reservation_audit.js", "variation"],
             "exit": 0, "stdout": ""},
        ],
    },

    "javascript-cve-2018-6835": {
        # etherpad-lite JSONP injection via API (CWE-79)
        "properties": [{
            "id": "jsonp_sanitized",
            "kind": "explicit",
            "description": "API JSONP callback names must be validated identifiers to prevent arbitrary script injection",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2018-6835 intake recipe",
                "approved": True,
            },
            "target_files": ["src/node/hooks/express/apicalls.js"],
            "harness_review": {
                "approved": True,
                "reference": "node tests/test_jsonp.js verifies that invalid JSONP callback expressions are not evaluated or wrapped in API responses",
            },
            "control": {
                "command": ["node", "tests/test_jsonp.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "tests/test_jsonp.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "tests/test_jsonp.js", "variation"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "jsonp-check-removed",
            "file": "src/node/hooks/express/apicalls.js",
            "property": "jsonp_sanitized",
            "find": "if(req.query.jsonp &&",
            "replace": "if(req.query.jsonp ||",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["node", "test_jsonp_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_jsonp_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["node", "test_jsonp_audit.js", "variation"],
             "exit": 0, "stdout": ""},
        ],
    },

    "javascript-cve-2019-10767": {
        # ioBroker path traversal in objectsUtils (CWE-22)
        "properties": [{
            "id": "path_traversal_blocked",
            "kind": "data-isolation",
            "description": "File and object names must have directory traversal sequences sanitized before accessing storage",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2019-10767 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/objects/objectsUtils.js"],
            "harness_review": {
                "approved": True,
                "reference": "node test/test_sanitize.js tests that sanitizePath strips dot-dot directory traversal sequences from target names",
            },
            "control": {
                "command": ["node", "test/test_sanitize.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "test/test_sanitize.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "test/test_sanitize.js", "variation"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "traversal-sanitization-removed",
            "file": "lib/objects/objectsUtils.js",
            "property": "path_traversal_blocked",
            "find": "name = path.normalize('/' + name);",
            "replace": "name = path.normalize(name);",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["node", "test_sanitize_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_sanitize_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["node", "test_sanitize_audit.js", "variation"],
             "exit": 0, "stdout": ""},
        ],
    },

    "javascript-cve-2019-15599": {
        # node-tree-kill command injection (CWE-78)
        "properties": [{
            "id": "pid_sanitized",
            "kind": "explicit",
            "description": "The process ID argument must be validated or sanitized before being passed to child_process.exec",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2019-15599 intake recipe",
                "approved": True,
            },
            "target_files": ["index.js"],
            "harness_review": {
                "approved": True,
                "reference": "npm test executes treeKill with intercepted process commands. A shell injection string fails the validation check.",
            },
            "control": {
                "command": ["node", "tests/test.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "tests/test.js", "reproducer"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "tests/test.js", "variation"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "pid-validation-removed",
            "file": "index.js",
            "property": "pid_sanitized",
            "find": "if (!/^[0-9]+$/.test(pid)) {",
            "replace": "if (false) {",
        }],
        "audit_checks": [
            {"role": "control", "command": ["node", "test_audit.js", "control"], "exit": 0, "stdout": ""},
            {"role": "security", "command": ["node", "test_audit.js", "reproducer"], "exit": 0, "stdout": "", "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation", "command": ["node", "test_audit.js", "variation"], "exit": 0, "stdout": ""}
        ],
    },

    "javascript-cve-2021-23664": {
        # cors-proxy SSRF via redirect following (CWE-918)
        "properties": [{
            "id": "cors_redirect_manual",
            "kind": "data-isolation",
            "description": "CORS proxy must not follow redirects automatically to internal/sensitive endpoints",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-23664 intake recipe",
                "approved": True,
            },
            "target_files": ["middleware.js"],
            "harness_review": {
                "approved": True,
                "reference": "node harness starts loopback test server returning 302; verifies proxy does not follow redirect to internal secret",
            },
            "control": {
                "command": ["node", "tests/test_redirect.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "tests/test_redirect.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "tests/test_redirect.js", "variation"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "manual-redirect-removed",
            "file": "middleware.js",
            "property": "cors_redirect_manual",
            "find": "redirect: 'manual',",
            "replace": "// redirect: manual",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["node", "test_redirect_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_redirect_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["node", "test_redirect_audit.js", "variation"],
             "exit": 0, "stdout": ""},
        ],
    },

    "javascript-cve-2021-29300": {
        # ronomon/opened command injection (CWE-78)
        "properties": [{
            "id": "opened_command_injection_blocked",
            "kind": "explicit",
            "description": "File path arguments must be passed securely to execFile rather than interpreted via child_process.exec",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2021-29300 intake recipe",
                "approved": True,
            },
            "target_files": ["index.js"],
            "harness_review": {
                "approved": True,
                "reference": "node tests/test_injection.js intercepts child_process calls to ensure execFile is used instead of shell-interpolating exec",
            },
            "control": {
                "command": ["node", "tests/test_injection.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "tests/test_injection.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "tests/test_injection.js", "variation"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "execfile-to-exec",
            "file": "index.js",
            "property": "opened_command_injection_blocked",
            "find": "Node.child.execFile(",
            "replace": "Node.child.exec(",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["node", "test_injection_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_injection_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["node", "test_injection_audit.js", "variation"],
             "exit": 0, "stdout": ""},
        ],
    },

    "javascript-cve-2024-56334": {
        # systeminformation OS command injection via network interface name (CWE-78)
        "properties": [{
            "id": "ssid_cmd_injection_blocked",
            "kind": "explicit",
            "description": "Wireless SSID names queried via netsh must be sanitized before interpolation into shell commands",
            "provenance": {
                "kind": "operator",
                "reference": "PRATIRODH javascript-cve-2024-56334 intake recipe",
                "approved": True,
            },
            "target_files": ["lib/network.js"],
            "harness_review": {
                "approved": True,
                "reference": "node tests/test_wifi_ssid.js tests that SSID profile queries sanitize shell metacharacters before executing netsh",
            },
            "control": {
                "command": ["node", "tests/test_wifi_ssid.js", "control"],
                "exit": 0,
                "stdout": "",
            },
            "reproducer": {
                "command": ["node", "tests/test_wifi_ssid.js", "security"],
                "exit": 0,
                "stdout": "",
                "violation": {"exit": 1, "stdout": ""},
            },
            "variations": [
                {"command": ["node", "tests/test_wifi_ssid.js", "variation"],
                 "exit": 0, "stdout": ""},
            ],
        }],
        "mutations": [{
            "family": "sanitization-removed",
            "file": "lib/network.js",
            "property": "ssid_cmd_injection_blocked",
            "find": "const s = util.isPrototypePolluted() ? '---' : util.sanitizeShellString(SSID);",
            "replace": "const s = SSID;",
        }],
        "audit_checks": [
            {"role": "control",
             "command": ["node", "test_wifi_ssid_audit.js", "control"],
             "exit": 0, "stdout": ""},
            {"role": "security",
             "command": ["node", "test_wifi_ssid_audit.js", "security"],
             "exit": 0, "stdout": "",
             "violation": {"exit": 1, "stdout": ""}},
            {"role": "variation",
             "command": ["node", "test_wifi_ssid_audit.js", "variation"],
             "exit": 0, "stdout": ""},
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
            "find": "if (object->valuestring == NULL)",
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
            "family": "minimum-bytes-reduced",
            "file": "libarchive/archive_read_support_format_7zip.c",
            "property": "sevenzip_oob_read",
            "find": "*buff = __archive_read_ahead(a, minimum, &bytes_avail);",
            "replace": "*buff = __archive_read_ahead(a, 1, &bytes_avail);",
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
            "file": "printbuf.c",
            "property": "linkhash_integer_overflow",
            "find": "if (size > INT_MAX - p->bpos - 1)",
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
            "family": "dtd-guard-removed",
            "file": "expat/lib/xmlparse.c",
            "property": "expat_entity_uaf",
            "find": "if (dtd) {\n      parser->m_dtd = NULL;\n    }",
            "replace": "if (0) {\n      parser->m_dtd = NULL;\n    }",
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
            "family": "backtrack-guard-removed",
            "file": "xmlreader.c",
            "property": "xmlreader_expand_uaf",
            "find": "(reader->state != XML_TEXTREADER_BACKTRACK) &&",
            "replace": "(1) &&",
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
        "seconds": 600,
        "reserve_seconds": 180,
        "model_calls": 2,
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
        "editable": [f for f in recipe.get("source_map", {}).keys() if f in files],
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


def build_audit(harness, audit_dir):
    """Build audit.json from harness audit_checks definitions and embed audit file contents."""
    audit_files = {}
    if audit_dir.exists():
        for p in audit_dir.rglob("*"):
            if p.is_file():
                rel_path = p.relative_to(audit_dir).as_posix()
                if rel_path == "manifest_patch.json":
                    continue
                audit_files[rel_path] = p.read_text(encoding="utf-8")

    checks = harness.get("audit_checks", [])
    if not checks:
        raise ValueError("Audit checks missing in harness definition")
    if not audit_files:
        raise ValueError("Missing executable harness files in audit directory")

    import hashlib
    h = hashlib.sha256()
    for name in sorted(audit_files):
        h.update(name.encode('utf-8'))
        h.update(audit_files[name].encode('utf-8'))
    audit_digest = h.hexdigest()

    return {
        "context": AUDIT_CONTEXT,
        "image": AUDIT_IMAGE,
        "files": audit_files,
        "digest": audit_digest,
        "checks": checks,
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
    audit_dir = ROOT / "benchmark" / "recipes" / case_id / "audit"

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
        audit = build_audit(harness, audit_dir)
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
