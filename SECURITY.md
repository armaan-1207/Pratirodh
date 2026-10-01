# Security policy

PRATIRODH 0.2 is for trusted operators and controlled, contract-registered Python Flask fixtures. The target runner is not a service for arbitrary hostile uploads. The deployed dashboard is authenticated and read-only and has no Docker socket or execution privileges.

Report vulnerabilities privately to the repository owner through the repository host's private vulnerability reporting feature if available. Do not publish secrets, private evidence, or protected source code in public issues. Include affected version, reproducible controlled example, expected behavior, and observed impact.

Release security checks are described in docs/PROJECT_GUIDE.md. They include OWASP Top 10 2025 controls, dependency audit, application static analysis, executable integration checks, evidence integrity checks, and deployment health/access checks. This is a scoped engineering review, not OWASP certification or an external penetration test.

## Offline repair release

Local inference uses a fixed loopback-only, proxy-free, redirect-free Ollama adapter. Cloud adapters require explicit selection. Setup downloads are separate from runtime. The selected model digest and parameters are recorded; no model output can modify trusted assertions.

Static findings are unverified candidates. Version-2 command effects are observed by a supervisor after an isolated target process exits; credential profiles use separate processes. These controls cover trusted registered fixtures, not arbitrary hostile uploads. Human review labels are not authenticated identities, and approvals never replace source.

The dedicated Windows offline interpreter and native Ollama can be restricted by the supplied program firewall rules. The standard venv launcher forwards to a base executable and is unsuitable as the firewall program target. Firewall removal is explicit and limited to the two named project rules.
