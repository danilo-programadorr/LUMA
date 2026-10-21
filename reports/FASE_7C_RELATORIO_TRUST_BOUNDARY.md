# Fase 7C — fronteira de confiança da LUMA

Data: 2026-10-21. Responsável pela verificação: Codex. Escopo: D:/projetos/luma. Status: CONFIRMADO em implementação e testes locais; confiança alta para o escopo validado. Fase 7C concluída, sem autorização para fase seguinte. Produção não verificada.

## 1. Baseline

LUMA 0.2.0, commit 7B ada01cc344b9307f115069b580a52f1c55022145, árvore limpa e auditoria existente VERIFIED antes das alterações. Baseline 7A cb06235a3e7b53d097d4851d7cae34130e3c5b38. Branch criada: codex/fase-7c-trust-boundary. Autorização integral preservada em AUTORIZACAO_FASE_7C.txt.

## 2–5. Migração e principals

v0002_trust_boundary.py acrescenta grants normalizados, retention_policies e audit_chain; migra local-owner para HUMAN_OWNER e cria luma-runtime SERVICE_RUNTIME. AGENT_SERVICE/TOOL_SERVICE são contratos. v0001_initial.py não foi alterada. Upgrade explícito preserva dados e encapsula DDL/DML em transação SQLite; teste de falha confirma rollback para revision 1. Startup exige revision 2, não migra/reset automaticamente. Teste de banco 0001 com dados verifica campos anteriores, grants equivalentes e os três novos grants administrativos explicitamente autorizados.

## 6–9. Planos, credenciais e segredos

Rotas admin exigem HUMAN_OWNER; rotas runtime exigem SERVICE_RUNTIME. A identidade é derivada do bearer e reconsultada no banco. Runtime em admin e owner em runtime recebem 403. Segredos separados OWNER, RUNTIME, ADMIN_CONFIRM e KNOWLEDGE; alias legado LUMA_TOKEN não representa credencial de runtime. Duplicatas são rejeitadas. SecretRef contém somente referência. Environment sanitization retorna ambiente vazio por padrão; aceita opcionalmente só a credencial identificada como própria do runtime, sem repassar variáveis herdadas.

Tokens conhecidos e campos sensíveis são recusados em payloads e na fábrica model_input. Não são salvos em audit, action parameters, learning ou contratos exportados. Nenhum código de modelo recebe Settings/DB. Limite de entrada 16 KiB mantido; contexto validado pode conter até o limite de 2 MiB do cliente Knowledge. A primeira integração runtime revelou aplicação indevida do limite de entrada à saída; corrigida antes da candidata final. Resultado intermediário com essa falha foi preservado em FASE_7C_TESTES_VALIDACAO.txt.

## 10–12. Grants, revogações e precedência

Grants possuem grant_id, principal_id, capability, project_id/tool_id opcionais, scope, granted_by, created_at, expires_at e status. Capabilities do JSON histórico não autorizam; runtime inicia com quatro grants mínimos por projeto. Expirado/revogado/ausente nega. GET/POST grants e revoke são administrativos; autoatribuição é negada. Capabilities críticas exigem humano, grant administrativo e confirmação adicional para elevação. Serviços não recebem admin.* nem capacidades externas.

Ordem funcional: sistema bloqueado > revogação > tool desabilitada > projeto desabilitado/fora de escopo > grant > default deny. Identidade/sessão são pré-condições. Admin humano permanece disponível em LOCKED para recuperação autorizada; unlock continua com capability específica e confirmação.

## 13–15. Propostas, consentimento e approval

Runtime pode propor ações, nunca aprovar, desbloquear ou conceder grants. Backend define MODEL_PROPOSED, origin_id, session_id, correlation_id, risco e policy. AUTO é elegibilidade futura, CONFIRM aguardaria aprovação e DENY é terminal para aprovação. Calendar/Tasks recebem DENIED no runtime por falta de autoridade/tool habilitada. Nenhum executor existe.

USER_INTENT, AUTHORIZATION e APPROVAL são conceitos separados. Frase do modelo “o usuário aprovou” não gera HUMAN_DIRECT. Somente rota humana autenticada produz origem humana. Origem de ação nova integra hash de escopo; hashes legados preservados. Rota administrativa histórica mantém proposta/decisão/consumo sem execução. AUTO de HUMAN_DIRECT para Calendar/Tasks continua requisito futuro condicionado a todos os controles.

## 16–17. Retenção e audit

Cinco categorias NO_AUTO_DELETE, com preview administrativo de contagem e expiração; zero registros elegíveis para exclusão. Não há purge nem política regulatória presumida. Audit encadeado por sequência/previous_hash/event_hash e âncora transacional. Verificação detecta alteração, remoção e perda de âncora; erros fecham acesso. Histórico encadeado na migração não comprova integridade anterior à migração. É TAMPER-EVIDENT; administrador do SO pode reescrever cadeia/âncora.

## 18–19. Sessões e learning

Sessão humana vincula principal humano, runtime e projeto ativo. Sessões históricas permanecem sem vínculo runtime; novas sessões exigem humano autenticado. Não há troca arbitrária de projeto. Permissão efetiva usa interseção dos dois principals, projeto, tool e grants. Revalidação antes/depois da consulta detecta revogação durante I/O. Sessions/touch não modifica identidade/projeto. Learning de runtime depende de grant explícito adicional, permanece MODEL_PROPOSED/PROPOSED e não pode ser validado/promovido pelo workflow legado.

## 20–23. Contratos futuros

ModelInputContext só contém mensagem, resumo permitido, projeto, KnowledgeContext, tools limitadas e IDs de ações pendentes. ModelDecision não aceita grant/approved/unlock/identity override/permission override. ToolCallProposal representa dados de proposta, sem executor. AgentExecutionContext contém identidade runtime e capacidades limitadas, nunca OWNER automático.

Calendar continua PLANNED/DISABLED: calendar.read, availability, create, update, delete e reminders. Tasks continua PLANNED/DISABLED: tasks.read, create, update, complete, reopen, organize e delete. Aliases/contratos anteriores preservados. Gemini/ADK são somente contratos, sem SDK, chave, chamada ou agente executável.

## 24. LUMA Web

Requisito oficial registrado em docs/LUMA_WEB_REQUISITOS.md: web responsiva desktop/celular, texto, voz, conversa contínua e futura entrada de arquivos/imagens. Núcleo visual com IDLE, LISTENING, THINKING, SPEAKING, WAITING_APPROVAL e ERROR. SPEAKING pulsa/expande/contrai e reage à amplitude/ritmo/vibração; LISTENING e THINKING têm comportamentos próprios. Nenhum frontend implementado.

## 25. Endpoints

Contratos exatos em contracts/openapi.json. Admin: grants create/read/revoke, retenção e preview, audit/verify, além das rotas anteriores. Runtime: status, knowledge/query, actions/propose, actions/{id}, sessions/{id}, sessions/touch e learning/propose. Mutações exigem Idempotency-Key, escopo atual é revalidado antes do replay, e retorno idempotente é snapshot histórico.

## 26–31. Evidências de validação

Evidências locais de 2026-10-21, verificador Codex, candidata 0.3.0:

- FASE_7C_TESTES_RELEASE.txt: **156 passed, zero skips**, 134,98 segundos; um aviso de depreciação Starlette/httpx.
- FASE_7C_INTEGRACAO_KNOWLEDGE.json: oito categorias, comparação real por HTTP do owner e runtime com Knowledge direta; results/sources/warnings/permission_status/status/confidence idênticos. Serviços de teste e worker Knowledge encerrados.
- FASE_7C_RESTART_REAL.json: dois processos distintos, saídas 0/0, preservação de grants, revocations, retenção, cadeia auditável, runtime principal, sessions, actions, approvals e estado LOCKED.
- FASE_7C_MIGRACAO_BACKUP.json: banco operacional 0001→0002, dados anteriores preservados; duas identidades, 27 grants e cinco políticas de retenção. Backup anterior preservado; backup 0002 restaurado em banco temporário, integrity_check=ok, todas as tabelas e cadeia idênticas. Nenhum reset ou servidor operacional iniciado.
- FASE_7C_AUDITORIA.json: auditoria final da entrega e fontes protegidas. v0001 conferida contra o blob do commit 7B; DB, backups e ambiente virtual ignorados pelo Git.

A falha intermediária de limite de contexto foi corrigida e a suíte inteira repetida; não houve exclusão de teste ou skip para obter aprovação. As suítes incluem token ausente/trocado, principal inativo, owner sem grant, expiração/revogação, tentativa de admin pelo runtime, spoof de origem/identidade/aprovação, mass assignment, vazamento de segredo/audit, escopo de sessão, replay, revogação durante I/O, concorrência e rollback.

## 32–35. Versões, commit, limitações e próxima fase

LUMA Backend 0.3.0 validado localmente. Knowledge API 0.1.0, Cérebro 0.6.0 e Engine 1.4.0 permanecem preservados. Commit local desta entrega: `feat: adiciona fronteira de confiança da LUMA`, na branch `codex/fase-7c-trust-boundary`. O hash do commit que contém este relatório é registrado no recibo local `runtime/phase-7c-commit-receipt.json` e apresentado ao proprietário após o commit; evitar autorreferência impossível de hash dentro do próprio commit. Nenhum remote/push/deploy.

Limitações: separação lógica em processo confiável, sem sandbox de modelo executável; bearer local e confirmação adicional não são MFA; scanner não detecta universalmente segredos desconhecidos; audit sem âncora externa e verificação O(n) por append; SQLite e execução local, sem alegação de produção/PostgreSQL; runtime não possui tool externa nem geração. Um aviso de depreciação Starlette/httpx pode aparecer, sem skip mascarado.

Recomendação: submeter ao proprietário uma fase futura específica para o adaptador de modelo e seu isolamento, após revisão destes contratos. Esta recomendação não autoriza Gemini, ADK, agentes, Calendar, Tasks, frontend ou deploy. Parada ao fim da Fase 7C.
