# Fase 7B — Persistência durável e control plane local

**CONCLUÍDA E VALIDADA LOCALMENTE — LUMA Backend 0.2.0.** 108 testes distintos aprovados, integração Knowledge preservada, restart real validado e auditoria aprovada. Banco operacional inicializado em runtime/luma.db, ignorado. Nenhum serviço deixado ativo.

Data: 2026-10-21. Verificador/responsável: Codex, sob [autorização específica](AUTORIZACAO_FASE_7B.txt). Confiança alta para implementação e testes locais. Produção não verificada. Histórico 7A permanece no Git e nos relatórios anteriores; seus textos refletem a entrega anterior à criação do baseline.

## 1. Baseline Git e branch

Antes da implementação foram executados git status, auditoria existente, conferência de todos os hashes 7A, scan de padrões de segredos e git check-ignore para runtime/.venv/caches. Apenas os 33 arquivos da entrega validada 7A foram incluídos no primeiro commit:

`cb06235a3e7b53d097d4851d7cae34130e3c5b38` — `feat: cria núcleo inicial da LUMA`.

Depois foi criada e utilizada exclusivamente a branch `codex/fase-7b-persistencia-control-plane`. Sem remote/push. O commit atômico 7B é o que adiciona este relatório, criado após testes/auditoria; seu hash completo é informado na resposta final. Para obtê-lo depois: `git log -1 --format=%H -- reports/FASE_7B_RELATORIO_PERSISTENCIA_CONTROL_PLANE.md`. O próprio hash não é embutido neste arquivo, evitando autorreferência impossível no mesmo commit.

## 2. Banco, schema, migrações e repositories

SQLAlchemy **2.1.5** (linha 2.x) + SQLite local, sem serviço externo. `LUMA_DATABASE_URL` aceita SQLite apenas sob runtime, default runtime/luma.db. Cliente HTTP não fornece path/URL de DB. Banco, backups, ambiente e caches ignorados e excluídos do commit.

Schema v0001 explícito: schema_version, principals, projects, tools, agents, system_state, actions, approval_requests, approvals, revocations, sessions, learning, audit_events e idempotency. [Snapshot de schema](../contracts/database-schema.json). Entidades têm IDs, índices de principal/projeto, status, datas e snapshot JSON. Grants/roles/scopes são arrays auditáveis, bootstrap conhecido, sem endpoint genérico de alteração.

Migração versionada em `backend/migrations/v0001_initial.py`, comando `python -m backend.migrate upgrade`. Mecanismo equivalente mínimo em vez de Alembic: somente revisão 0001 nesta fase, transação explícita, idempotência e rejeição de schema parcial/desconhecido. Startup exige schema atual; nenhum create_all/reset silencioso. Alterações futuras precisam de nova revisão/testes. Repository concentra SELECT/INSERT/UPDATE/paginação via SQLAlchemy; regra de negócio não depende de SQL exclusivo SQLite. PostgreSQL não instalado/testado; configuração e manutenção precisarão de adaptador futuro.

Cada mutação começa com UPDATE de linha de coordenação antes de leituras de policy, serializando escritores no banco entre conexões/processos. Ausência/versão incorreta dessa linha falha fechado. Esse protocolo não usa lock Python como garantia de unicidade. Falha de DB retorna erro seguro, sem stack trace/valores SQL ao cliente.

## 3. Bootstrap, identities, projetos, tools e agentes

Bootstrap só em schema vazio; estado parcial rejeitado, estado existente nunca sobrescrito. [Bootstrap operacional](FASE_7B_BOOTSTRAP_LOCAL.json): um owner, um projeto, nove tools, nove agentes e um evento inicial, sem ações/aprovações. Segredos temporários usados apenas em memória para inicialização foram descartados, não persistidos. Nenhum servidor operacional foi iniciado para isso.

Principal local-owner persiste principal_type/display_name/status/datas, roles/scopes/capabilities/approval_level. Autenticação recarrega o principal ativo do DB; payload não altera identidade. Bearers continuam exclusivamente no ambiente, sem cópia ou token em claro no banco. Credencial adicional administrativa também é somente ambiente.

Registry durável contém apenas meu-gestor: nome/estado/endpoint/modo/enabled/datas/capabilities/metadados. Admin só altera name/status/enabled; não aceita URL arbitrária. Endpoint local inicial vem de configuração e é persistido. Alteração posterior no ambiente não reescreve DB e divergência de rota falha fechada. MechAI não implementado.

Knowledge é ENABLED_LOCAL. Calendar, Tasks, GitHub, Firebase, Codex, Analytics, Google Ads/Meta e PC Runner continuam PLANNED/DISABLED. Desabilitação persiste após restart. Endpoint enable só permite Knowledge; teste alterando diretamente estado de ferramenta externa confirmou que isso não cria executor.

Nove agentes persistidos PLANNED, conforme lista específica 7A: LUMA, Produto, Desenvolvimento, Codex/Engenharia, QA, Segurança, Dados/Analytics, Growth/Marketing e Conteúdo/Social. Nenhum agente executável.

## 4. Capabilities, revogações e estado global

Grants administrativos explícitos: status/state, projects, tools, agents, approvals, actions, revocations, audit, sessions e learning, com separação read/manage/unlock onde aplicável. OWNER textual isolado não autoriza operações. Teste removeu grant mantendo role OWNER e confirmou 403.

Revogações persistem revocation_id, principal, projeto, tool opcional, capability, reason, created_at/expires_at e revoked_by. Alvo inicial é o principal autenticado e projeto autorizado, sem troca arbitrária por payload. Expiração usa prazo absoluto; restart não remove revogação nem renova grants. Revogação administrativa de escopo bloqueia operação agregada correspondente. Não existe remoção genérica via HTTP nesta fase.

RUNNING/PAUSED/LOCKED são duráveis; alteração/audit/idempotência são atômicos. Política 7A preservada: PAUSED e LOCKED bloqueiam Knowledge. Admin exige capabilities e permanece disponível para recuperação autorizada. Saída de LOCKED requer admin.state.manage + admin.state.unlock, confirmation UNLOCK_LUMA e X-Admin-Confirmation válido, distinto do bearer.

## 5. Actions, approvals, transições e idempotência

ActionRequest é persistido com parâmetros e hash estável, principal/projeto/tool/capability, risco/requisito calculados pelo backend, status/datas. Proposta não executa. Não se aceita requirement/status/principal arbitrário no create. Estados de execução existem no contrato futuro, mas não há caminho HTTP para EXECUTING/SUCCEEDED/FAILED nesta fase. Cancelamento apenas de estados não terminais permitidos.

ApprovalRequest pendente é registro separado. Decisão administrativa grava ApprovalRecord, status de action/request e audit na mesma transação. Aprovação exige principal/capability, HUMAN_DECISION, hash scope da ação e segredo adicional no header. approved=true é inválido. Record contém decision, scope, created_at, expires_at de cinco minutos, consumed_at e reason. Mudança de parâmetros, principal, outra action, expiração, segunda decisão e consumo repetido são rejeitados.

Consumo via admin é **validação sem execução**: marca consumed_at, cancela action e atualiza approval_request/audit atomicamente, retornando execution_performed=false. Assim testa single-use sem executar ferramenta planejada ou inventar sucesso. Aprovação não concede capability nem habilita tool. Retry com mesma chave devolve snapshot original; nova tentativa de consumo falha. Estado/objeto atual deve ser consultado em GET.

Idempotency-Key obrigatório em mutações, 8–128 caracteres restritos; chave armazenada só em hash escopado ao principal. Fingerprint inclui operação/target/payload. Repetição legítima não duplica, payload diferente com mesma chave dá 409. Autorização/confirmador são reavaliados antes do replay; replay não sobrescreve estado posterior.

## 6. Sessões, aprendizado, auditoria e configuração

Sessões persistem metadados mínimos/dono/projeto/status/datas, com expiração de 24h e encerramento explícito. Nenhuma conversa integral. Learning candidates persistem source/claim/evidence/confidence/status/datas com escopo; PROPOSED pode virar VALIDATED/REJECTED, PROMOTED é negado enquanto write-back permanece desabilitado. Memória, conhecimento e candidato continuam conceitos separados; nenhum candidato vira verdade canônica automaticamente.

Audit durável append-oriented inclui event_id/timestamp/principal/project/event_type/tool/action/result/correlation. Alteração de negócio e audit de mutação compartilham commit/rollback. Não existe endpoint genérico de edição; Repository proíbe UPDATE de audit/idempotency. Auditoria HTTP adicional registra resultados fora da transação de domínio; falha adicional após commit pode levar cliente a repetir com mesma chave, sem efeito duplicado.

Audit não contém token, query, chunks, intent, parameters, documentos/conversa ou finanças. Campos necessários nas entidades passam por filtro de segredos conhecidos/padrões e chaves de credenciais; usar referências mínimas e dados sintéticos continua necessário. Não é detector universal de segredo desconhecido nem ledger resistente a administrador do SO.

Configuração estática/segredos ficam no ambiente; estado operacional no DB. Histórico/packages são defaults do bootstrap persistidos, não sobrescritos no restart. Banco e backups locais não são cifrados pelo serviço; proteção depende de permissões do SO. Backup transacional SQLite implementado e testado com restauração do snapshot; conexões fechadas explicitamente. Reset manual inequívoco, com aplicação parada, confirmação RESET_LOCAL_LUMA e arquivo original arquivado, documentado no README. Nenhum reset foi executado.

## 7. API administrativa e segurança

[OpenAPI](../contracts/openapi.json), [schemas administrativos](../contracts/admin-models.json) e [matriz completa](../docs/CONTROL_PLANE_7B.md). GETs: state/projects/tools/agents/actions/{id}/actions/approvals/approval-requests/revocations/sessions/learning/audit. Mutações limitadas a state, metadata de project, tool enable/disable, revocation, action/cancel, decision/consume, session/close e learning/status. Leituras paginadas no SQL, até 100 registros, filtradas por principal/escopo.

Bind 127.0.0.1, CORS desativado, forwarded headers ignorados. Todas as rotas admin autenticadas e com capabilities específicas. Campos desconhecidos/mass assignment rejeitados; tabelas/paths/SQL/URLs não são selecionáveis pelo cliente. SQL parametrizado. Recursos inexistentes/fora do escopo não produzem dados de outro projeto. Segredo em payload administrativo rejeitado antes de armazenamento e não aparece em logs/DB nos testes.

Confirmação humana aqui significa declaração pelo canal administrativo autenticado com credencial adicional. **Não é MFA/prova de presença humana de produção.** Futura camada LLM não pode receber esses segredos/grants. Nesta fase não há LLM integrado nem executor capaz de chamar a administração autonomamente.

## 8. Testes, transações, concorrência e restart

[Suíte final](FASE_7B_TESTES_RELEASE.txt): **108/108 aprovados, nenhum skip**. São 65 testes de regressão adaptados ao banco temporário e 43 testes novos. Um warning conhecido de depreciação Starlette/TestClient httpx permanece, sem falha. Após a suíte, o fechamento explícito de conexões de backup recebeu [verificação dirigida adicional](FASE_7B_TEST_BACKUP_FINAL.txt), sem inflar o total de casos distintos.

Cobertura: schema/migração repetida e incompatível, bootstrap, principal/capabilities, admin auth, escopo, kill switch, tools, revogações, action/approval, idempotência, sessões/expiração, learning, audit, segredo, SQL/path injection, mass assignment, forja/replay, corrupção da linha de coordenação, rollback e backup. Falha injetada no audit reverte criação de action/request/idempotency e decisão de approval/action/request sem estado parcial.

Concorrência entre Store/engines distintos: duas decisões, dois consumos, revogação simultânea, mudança concorrente de estado e mesma idempotency key. Uma decisão/consumo efetivo, sem duplicação; LOCKED não é desfeito por corrida sem confirmação. Escala local pequena, sem claim de stress test de produção.

[Restart real](FASE_7B_RESTART_REAL.json): dois subprocessos LUMA distintos, servidores loopback, encerramento normal exit 0 e reabertura do mesmo DB. Preservados LOCKED, revogação, tool desabilitada, action, approval, session, candidato e audit; só um bootstrap e Knowledge continuou bloqueado. Teste complementar fechou/reabriu Store e confirmou todos os registros, incluindo consumo já realizado e replay negado.

[Integração Knowledge](FASE_7B_INTEGRACAO_KNOWLEDGE.json): oito assuntos, LUMA HTTP → Knowledge API → engine. Comparação integral de results/sources/warnings/permission_status/project/status/confidence preservada. Versões mantidas e nenhuma resposta gerada. Knowledge desligada mantém LUMA disponível/degradada; servidores e worker terminam. Holdouts/ranking/corpus não alterados nem retunados.

Comandos principais:

```powershell
.\.venv\Scripts\python.exe -m backend.migrate upgrade
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:LUMA_TEST_KNOWLEDGE_WORKSPACE='D:\cerebro do gestor'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=runtime/tests-7b-release
.\.venv\Scripts\python.exe audit_workspace.py
```

As primeiras verificações identificaram resolução incorreta da raiz runtime e uma chave de teste curta; foram corrigidas antes da aprovação final. Revisão adicionou proteção à ausência da âncora transacional. Escrita fora da raiz original do chat e sockets locais passaram pelas revisões de acesso autorizadas; não houve bypass.

## 9. Auditoria, versões, arquivos e limitações

[Auditoria final](FASE_7B_AUDITORIA.json) aprovada: 37 hashes da entrega Fase6, 166 da 5F e 763 arquivos da fonte preservados; source main@9fe7fd3a69a537f9e67953b7028e64c676a48547. Repositório financeiro também limpo, consultado somente via Git read-only. Sem alteração em app/Cérebro, SDK Google/Gemini/ADK, frontend, remote ou push. Migração no Git; runtime/DB/.venv/caches ignorados. Scan é heurístico, combinado com testes e inspeção de configuração/contratos.

Mudanças principais: database/repository, migração/runner, Control durável, schemas/router admin, wiring de auth/routing/Knowledge, manutenção backup, testes, dependências fixadas, contratos e docs. Inventário com hashes em FASE_7B_HASHES_ENTREGA.json. Módulos de memória anteriores permanecem para referência/regressão conceitual, mas não são instanciados pela aplicação; Control/Store são autoridade operacional.

Versões: LUMA Backend **0.2.0**, Knowledge API **0.1.0**, Cérebro **0.6.0**, engine **1.4.0**. Python3.13.1/FastAPI0.156.2/Pydantic2.14.1/Uvicorn0.54.0/SQLAlchemy2.1.5. PostgreSQL não validado, runner de migração só v0001, grant management/multiusuário/OAuth/MFA não implementados, DB sem cifragem própria, audit sem retention automática/garantia criptográfica. Timeout HTTP por operação, sem SLA; SQLite coordena escritores com limite local de contenção. Não há ações externas, write-back, IA, frontend, agentes executáveis ou deploy.

## 10. Commit e recomendação

Baseline 7A: `cb06235a3e7b53d097d4851d7cae34130e3c5b38`. Commit 7B local atômico com mensagem `feat: adiciona persistência e control plane da LUMA`, criado após evidências e auditoria; hash completo na entrega final. Nenhum remote/push.

Próxima fase, somente com autorização: definir fronteira de autenticação administrativa e gestão de grants/retention antes de conectar agentes ou ferramentas mutáveis. Persistência e aprovação administrativa não são autorização para essas integrações.

**Parada da Fase 7B.** Não conectar Gemini/Calendar/Tasks, instalar ADK, criar frontend/agentes, fazer deploy ou push. Aguardar autorização explícita.
