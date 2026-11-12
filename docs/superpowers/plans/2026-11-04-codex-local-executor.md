# Codex Local Executor Implementation Plan

> Execução inline com superpowers:executing-plans e testes antes das mudanças de comportamento. Sem commits.

**Goal:** Codex subordinado ao pipeline existente, com workspace lógico, sandbox nativo, ciclo durável e aceitação separada.
**Architecture:** Control Plane conserva toda autoridade; extensão assinada do canal existente; executor local resolve mapa privado e usa MXC explicitamente, sem fallback inseguro.
**Tech Stack:** Python/FastAPI/SQLAlchemy, PostgreSQL local, Windows MXC, Codex CLI 0.166.0, React.
**Spec:** C:/Users/Danil/.codex/attachments/3b0d88b1-8f32-4fee-aae5-b5cc0b81214f/Texto colado.txt (310 seções).

## Global Constraints
- Baseline 1093; backend 0.6.0rc1, Web 0.1.0-rc.1; schema 8 inicial.
- Sem commit/push/deploy, cloud, instalação, atualização, credenciais novas ou alterações em projetos protegidos.
- Sem modelo antes de preflight e aprovação real; custo desconhecido exige decisão do Owner.
- CODEX_EXECUTION default disabled; LOCAL_DEVICE e alvo exato; ZERO retries semânticos.
- Não alterar migrations 1–8 nem protocolos v1 existentes.
- Biblioteca suspensa; sem integração do vault; nenhuma mudança global.
- Erros históricos preservados; testes simulados nunca equivalem à aceitação real.

## Review Focus
- Escapes/corridas Windows e ferramentas internas além do comando launcher.
- Autorização one-shot em crash, reserva e resultado tardio.
- Proibição de rede de tarefa e vazamento de credenciais por subprocessos.
- Cancelamento efetivo da árvore, heartbeat e perda do Control Plane.
- UI canônica, auth_time e detalhes do escopo.

## Tasks
- [x] 1. Preflight sem modelo: versão, hash, login sanitizado, probe nativo MXC com root deny, subpath deny, rede negada.
  Evidence: FASE_7F_E_SANDBOX_FILESYSTEM_PREFLIGHT_dc299cd336e94e659a074dec0d52d480.json. Rede loopback negada com 10013. Config/hook hashes iguais.
- [x] 2. Contratos estritos e mapa local: backend/codex/contracts.py, device_agent/codex_workspace.py; testes de paths, fingerprint, limites e snapshots.
- [x] 3. Autoridade: schema/migration 9 somente para workspace_registry lógico; backend/codex/service.py e api.py; action/proposal/job existentes. Assinaturas e one-shot.
- [x] 4. Executor local: adapter, markers, subprocess containment, broker de validação e perfis nativos. Fake runner separado; Codex real gated.
- [x] 5. UI e integração do agente: mostrar escopo/Codex, estados, resultados, cancelamento, grant por fluxo oficial.
- [ ] 6. PostgreSQL e regressões; preflight real; aceite real somente após gates; auditoria/secret scan e relatório final.

## Rulings
- Trabalhar no checkout/branch de fase existente: ele contém as implementações não commitadas da baseline; um worktree de HEAD as perderia. Não limpar nem mover trabalho.
- Override MXC por invocação, sem persistir seleção global, sem administrador. Probes são subprocessos reais sem modelo, não aceitação Codex.
- Falhas iniciais de parser e inicialização de arquivo PowerShell preservadas como diagnóstico; comando inline confirmado sem alterar ExecutionPolicy.
- Separar conectividade do cliente e rede dos comandos. Não conceder shell geral ao modelo.
- Rever mecanismo de comandos internos antes da candidata: apenas permitir executável do launcher é insuficiente.

Task 2: complete — 21 testes workspace/profile PASS. A rodada RED do canal usou basetemp fora de runtime e falhou antes do serviço; não conta como prova RED do comportamento. Corrigida a invocação para seguir a política existente, sem flexibilizar database_path.

Task 3: signed-channel candidate 17 PASS (SQLite real, verifier simulado). Migration 9 apenas em bancos de teste; banco Owner schema 8 preservado.
Task 4: core adapter/runner 13 PASS; invocation/broker 4 PASS; scope 8 PASS. Watchdog RED demonstrou efeito após timeout enquanto callback bloqueava; GREEN agora encerra independentemente. Nenhum modelo invocado.
Ruling: modelo sem shell geral; broker stdio aceita somente validate sem argumentos, no máximo duas chamadas locais. Validação roda no MXC com rede negada. Não altera hooks/configuração globais; opcionais do processo executor não são carregados; controles gerenciados permanecem aplicáveis.

Task 5: UI candidate 4 testes novos PASS + 8 remotos preservados; typecheck/build PASS. Lint teve 1 warning de cleanup, corrigido sem alterar desenho. Discovery 3 PASS e agente fake integrado 4 PASS, com resultado recuperado sem segunda execução.
Preflight: CLI oferece --no-daemon, agora obrigatório para manter processo dentro do Job Object. Desabilitados no executor shell/apps/plugins/computer/browser/multi-agent/hooks opcionais/code-mode; sem bypass ou alteração global.
Native validator: PASS no MXC + Job Object, sem modelo. Redaction/UTF-8 RED->GREEN: seis casos; não conta como segredo real.

Ruling: fixture ganha Git próprio vazio (sem commit), para não enviar ao modelo metadados do repositório pai. Init é preparação do fixture, nunca uma permissão Git do job. Config local sintética; tarefas não escrevem .git.
Ruling: snapshot_hash vincula conteúdo exato à proposta. Mudança antes do contexto/processo bloqueia; descoberta pode atualizar somente esse metadado, nunca mapping/grant. Perfil do modelo nega raiz e concede apenas arquivos selecionados; validador usa fixture somente leitura, -B e somente test_calc.py.

Final local candidate 2026-11-05: 1,198 unique PASS =975 backend+95 PG+96 frontend+32 browser; baseline1093 preserved. Full HTTP configuration skip closed by targeted correctly configured PASS, not hidden. Independent review counterexamples resolved; fresh local/PG/UI regressions passed. Local policy fingerprint now includes modes/binary/model, enforced again in executor. Extraneous extension payload fields rejected.

Native registry probe opened no writable handle and wrote no values. Final validator PASS; config sandbox probe PASS with supported subcommand options; exec-only strict/ignore flags checked through help, not a model call. Process-tree test now confirms descendant PID termination. Source changes, tests and raw failed diagnostics preserved.

Owner PostgreSQL migrated8->9 only after verified dump; all preexisting rows unchanged immediately after. Control Plane reloaded in known local process, signed discovery PENDING_OWNER_GRANT, no Code grants/jobs, library remains suspended. Real stagesB/C/D/E and final post-real audit remain pending cost+OwnerUI gates. No new phase, commit, push, deploy or global configuration changes.
