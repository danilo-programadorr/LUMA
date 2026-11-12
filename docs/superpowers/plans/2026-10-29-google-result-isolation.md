# Google Result Isolation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. No subagents or new checkout: preserve the explicitly designated dirty workspace and no-commit constraint.

**Goal:** Propagate failures immediately and display unmodified Google suggestions with default/self navigation safely.
**Architecture:** Existing iframe remains for compatible artifacts; incompatible navigation uses an ephemeral isolated top-level document. Only authenticated Google delivery can issue a one-use display capability.
**Tech Stack:** Existing Python/FastAPI/Pydantic, React/TypeScript, browser CSP, Playwright. No dependency installation.
**Spec:** docs/superpowers/specs/2026-10-29-google-result-isolation-design.md and Owner correction attachment ef8856c4-3c2a-480c-b41d-aaada18fffd3.

## Global Constraints

Maximum6 accumulated real calls;1 already consumed. No real calls during correction; do not reset ledger. HTML opaque/unmodified, no persistent answers/URLs/HTML, no tracking, no script supplied by Google, no new cloud/API/credential, commit/push/deploy or next phase.

## Review Focus

- Missing/_self targets must reach direct SRP without target rewriting.
- Malicious scripts/storage access remain blocked in isolated document.
- Expired, consumed or wrong-owner delivery never replays content or calls provider.
- Failed reply is accepted immediately while incomplete successful reply remains rejected.
- Popup capability is one-use, short-lived, display-only and absent from persistent data/logs.

### Task1: Original failure propagation

- [x] Add failing API regression with real SQLite service path.
- [x] Restrict display-artifact requirement to COMPLETED in backend/research/service.py.
- [x] Verify84 research tests and11 isolated PostgreSQL tests. Original rows untouched.

### Task2: Navigation contract and isolated document

Files: backend/research/{contracts.py,provider.py,display.py,service.py,api.py}; backend/tests/test_google_window.py.
Interfaces: GoogleDisplayArtifact.presentation; render_google_display(result)->(bytes,headers); service.open_display(ticket)->response; GET /research-display/{ticket} consumes RAM capability.
- [x] Add and observe red targetless navigation regression.
- [x] Preserve iframe validation; allow safe native targets only in isolated-document mode.
- [x] Keep HTML original in bounded RAM delivery; issue random43-character one-use path after owner check.
- [x] Render escaped answer/citations with original suggestion HTML and restrictive sandbox/CSP. Only hash-pinned expiry code may execute; Google scripts rejected.
- [x] Test expiry/replay/storage and no persistence against real service.

### Task3: Frontend and browser integration

Files: web/src/auth/client.ts, web/src/components/luma/research-panel.tsx, web/e2e/google-window.spec.mjs, test-only HTTP fixture.
- [x] Add metadata-only live-window UI; resolve only exact local display path, user click opens noopener tab.
- [x] Test default/_self/_blank navigation, intact HTML, XSS/storage blocked, refresh/expiry safe, no automatic retry/provider calls.
- [x] Run full backend/PG/frontend/browser, typecheck/lint/build, audit and secret scan as appropriate to final changes; confirm ledger still1.
- [x] Restart only the local backend, preserve Owner identity, and report operational acceptance still pending before resuming remaining authorized calls.


## Execution ledger

- Task1: red API regression observed400/RESEARCH_ATTRIBUTION_UNAVAILABLE; one-line COMPLETED guard;84 research tests and11 PostgreSQL tests PASS; local CP restarted, no new real calls.
- Task2: targetless HTML red reproduced; presentation mode and one-use isolated document implemented;6 local service/retention tests PASS before review.
- Review: one P2 finding, unclosed opaque style could swallow trailing cleanup script. Red regression reproduced missing script; script moved before opaque snippet, artifact unchanged. Browser variant added. No other actionable finding reported; no re-review or paid calls.
- Ruling: use isolation equivalent expressly permitted by Owner instead of changing targets/HTML — preserves provider payload; tradeoff is a temporary additional tab for incompatible navigation.
- Ruling: preserve designated dirty workspace and no-commit instruction; no new worktree, commits or cleanup/deletion of plan files.

- Fechamento local:881 testes únicos PASS; PostgreSQL74, frontend64 e navegador21; typecheck/lint/build PASS; auditoria VERIFIED e secret scan PASSED. Serviços locais reiniciados e saudáveis; contador1/6 preservado. Precheck PASS, rearmado somente o saldo5; nenhuma chamada real nesta correção. Aceitação real da candidata segue pendente no PowerShell do Owner.

- Seguimento da chamada2: defectUTF-8 comprovado com SDK; índices convertidos para pontos de código, frontend alinhado e diagnóstico limitado a rótulos fixos.100 testes afetados backend,74 PostgreSQL,65 frontend e21 navegador PASS; consolidado891, baseline881 preservada. Contador2/6, sem chamada nova, saldo4. Causa específica da chamada2 não comprovável com telemetria antiga; real pendente. Incidente de reporter e substituição explícita de evidência histórica documentados em PROVIDER_REPORT_INCIDENT.json.
