# Identity trust boundary

2026-10-25 — 7F-B local candidate. Implementation/test evidence plus explicitly authorized real Identity Platform setup; see the sanitized real-auth report for acceptance status.

Browser/SDK -> signed Identity Platform ID token -> Google cryptographic verification -> explicit claims validation -> canonical persistent UID binding -> immutable AuthenticatedOwnerPrincipal -> existing canonical policy/grants.

UID in body/query/custom headers, matching email or profile, client approval flags, runtime credentials and legacy Owner token cannot substitute for the binding. Authentication does not approve an action or issue an execution authorization. Runtime and executor remain separate principals and never obtain Owner authority.

Owner bootstrap is exceptional: authenticated Google identity plus one-time local code, atomic database singleton and durable attempt counter. It cannot automatically bind the first Google login. DB transaction locks serialize concurrent claim attempts. HTTP schemas forbid extra fields. No user-selected internal principal id is accepted.

All /v1 routes use a centralized boundary: /v1/runtime/* SERVICE_RUNTIME; /v1/device/* SERVICE_EXECUTOR; remaining admin/execution routes HUMAN_OWNER. /v1/owner/bootstrap requires validated identity and code; /v1/owner/me requires the binding. Public /health is sanitized. Internal administration to generate a code is terminal-only. See reports/FASE_7F_B_ROUTE_INVENTORY.json. CORS permits localhost/127.0.0.1:5173 only, never wildcard; rejected origin is403. No cookie session is introduced, bearer tokens are not ambient credentials.

Residual scope: real Identity Platform setup/login was authorized and exercised; auth revocation beyond expiration and distributed rate limiting need future deployment review. No cloud deployment, enrollment, polling, remote job, Calendar, Tasks, browser/desktop automation or real Codex execution exists in this phase.
