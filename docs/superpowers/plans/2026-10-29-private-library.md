# Private Library Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. Steps use checkbox tracking; Owner delegated decisions and execution. One final focused review, no per-task agents.

**Goal:** Import local user files and retrieve cited private excerpts from the command center without external model calls.
**Architecture:** Local encrypted store and hashed lexical index, signed device protocol, canonical metadata/queue in existing Control Plane, authenticated Knowledge UI.
**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy/PostgreSQL, cryptography/DPAPI, SQLite derived index, pypdf 6.21.4, React/TypeScript.
**Spec:** docs/superpowers/specs/2026-10-29-private-library-design.md

## Global Constraints

No paid calls/embeddings, private egress to model/web, cloud, new cloud API, credentials exported, commit/push/deploy, next phase, stable promotion or changes to protected external workspaces. Preserve original-six and final-three ledgers byte-for-byte. Preserve migrations 0001–0007 and Device Protocol v1. Use existing dirty feature checkout so preceding authorized local phases are included. No worktree reset or cleanup. Each task ends in evidence/hashes instead of commits, per Owner instruction. Permanent execution ledger is reports/FASE_7F_D_A2_PROGRESS.md; no plan scratch deletion.

## Review Focus

Project/device scope and current capability must be checked again on result delivery, including transient GET. SQLite/WAL/logs must not contain raw private content or index words. Concurrent clients sharing identity must serialize sequence+send. Unsupported/scanned/encrypted PDFs must not fabricate text. UI must not imply semantic search, active index or generated answers before those exist.

### Task 1: Local parser and encrypted retrieval
Files: backend/private_library/{contracts,extract,parser_worker,store}.py; backend/requirements/private-library.txt; backend/tests/test_private_library_store.py.
- [x] Write RED tests for synthetic TXT/MD/PDF pages, unsupported/scanned/encrypted/oversized input, encrypted at rest, tampering, project isolation, idempotent import, restart and ranked citations.
- [x] Implement extraction subprocess (15 s, scrubbed environment), AES-GCM/DPAPI and HMAC-token SQLite index. Interfaces: LibraryStore(root, protect_key=..., device_id=...), ingest(project_id, title, extension, raw_bytes)->SourceMetadata, retrieve(project_id, query, source_ids)->list[PrivateExcerpt].
- [x] GREEN affected unit suite and record results. Install only pinned pypdf requirement; no other existing locks changed.

### Task 2: Canonical authority and signed protocol
Files: backend/private_library/{schema,service,api}.py; backend/migrations/v0008_private_library.py; backend/{migrate,control_plane_app,owner_auth}.py; backend/app/database.py; backend/tests/test_private_library_channel.py; backend/postgres_tests/test_private_library_pg.py.
- [x] RED grants, metadata registration, query/cancel/archive/expiry, current policy and transient no-persistence tests, migration fresh/upgrade/idempotency and concurrent PG cases.
- [x] Implement Owner routes and signed Library Protocol v1 per spec; add schema8 acceptance only, preserve auth policy. LibraryService receives Control and DeviceService; runtime uses existing DeviceAuthenticator. TTL memory separate from Google display.
- [x] GREEN new suites plus affected Owner/device/research and PG tests in isolated test DB.

### Task 3: Local agent and transport ordering
Files: library_agent/{__main__,client}.py; device_agent/transport_lock.py; device_agent/client.py; research_agent/client.py; scripts/{run_private_library,start_library_local}.ps1; .gitignore; backend/tests/test_private_library_agent.py.
- [x] RED shared identity transport ordering, no secret env, local explicit file import, scoped register, offline/revoke and no provider imports/calls.
- [x] Implement library-only outbound agent, metadata-only register, one-shot/loop query processing, protected local storage and launchers preserving parent env. Serialize sequence+send between clients, not protocol bytes.
- [x] GREEN new tests and existing device/research regressions; no actual Owner file or provider call.

### Task 4: Knowledge UI
Files: web/src/pages/KnowledgePage.tsx; web/src/components/luma/private-library-panel.tsx; web/src/auth/client.ts if bounded errors needed; web/src/pages/private-library.test.tsx; web/e2e/private-library.spec.mjs; backend/research/policy.py/service.py only for explicit local-area guidance.
- [x] RED real counts/empty/offline/capability UI, source scope/archiving, query states/citations, XSS, no content storage and no web fallback.
- [x] Implement functional authenticated private library view and local-import guide. Keep DEMO data separate. No upload/OCR/semantic/generated-answer claims.
- [x] GREEN frontend, types/lint/build and focused responsive browser cases.

### Task 5: Review and acceptance
- [x] Verify baseline 956 preserved, relevant backend/PG/frontend/browser suites; unit successes are not real Owner import evidence.
- [x] One independent focused code review; fix important findings RED/GREEN. No broad repeated review cycles.
- [x] Audit protected repos, protocol, legacy migrations, ledger hashes, permissions, egress, persistence and secret scan; generate sanitized final reports.
- [x] Only then backup/migrate local Owner DB if safe and needed, restart known server processes preserving PG/identity. Owner may activate PRIVATE_LIBRARY and select a real file for import; do not fabricate this interaction. End phase at that gate if missing.


Execution complete through local readiness,30/10/2026. Owner document acceptance is explicitly pending; no real import/approval fabricated. Evidence: reports/FASE_7F_D_A2_RELATORIO.json and execution ledger.
