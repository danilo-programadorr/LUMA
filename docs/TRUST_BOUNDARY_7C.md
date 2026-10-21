# Fronteira de confiança da LUMA — Fase 7C

Data: 2026-10-21. Responsável: Codex. Status: implementação local candidata; validação final no relatório da fase. Baseline: ada01cc344b9307f115069b580a52f1c55022145. Produção não verificada.

## Identidades e autoridade

HUMAN_OWNER/local-owner administra via /v1/admin com grants explícitos. SERVICE_RUNTIME/luma-runtime usa exclusivamente /v1/runtime. AGENT_SERVICE e TOOL_SERVICE são apenas tipos contratuais futuros. OWNER textual, capabilities no JSON histórico do principal, mensagens de modelo e origem de ação não concedem autoridade.

Grants são linhas normalizadas, com principal, capability, projeto, ferramenta, scope, autor, datas e status ACTIVE/REVOKED/EXPIRED. Expiração é calculada a cada uso mesmo quando o status materializado ainda é ACTIVE. Sem grant válido: DENY. A revogação nunca é anulada por outro grant. Elevação exige grant humano apropriado; grant para o próprio administrador é proibido. Serviços não recebem admin.* nem capabilities externas nesta fase. Não há API genérica de criação/troca de identidade.

Defaults do runtime: knowledge.read, runtime.session.read, runtime.session.write e runtime.actions.propose, restritos ao projeto herdado do owner na migração. runtime.learning.propose depende de grant humano explícito adicional. Os três novos grants administrativos da migração são admin.grants.read, admin.grants.manage e admin.retention.read, autorizados pelo escopo 7C. Os grants anteriores são preservados sem ampliar capacidades funcionais.

## Credenciais e separação

LUMA_OWNER_TOKEN, LUMA_RUNTIME_TOKEN, LUMA_ADMIN_CONFIRM_TOKEN e LUMA_KNOWLEDGE_TOKEN são distintos, nunca persistidos. LUMA_TOKEN permanece alias legado do owner para migração da operação local. Runtime sem token configurado fica inacessível. O backend confiável autentica ambas as identidades; o contexto do modelo e a interface do runtime não recebem Settings, conexão de banco ou segredos administrativos.

A separação nesta fase é lógica dentro de um processo local confiável, não isolamento contra execução arbitrária de código nesse processo. Nenhum modelo/worker é executado. O utilitário sanitized_worker_environment parte de ambiente vazio; a inclusão opcional de credencial própria é explícita. Uma implantação futura precisa combinar esse contrato com isolamento de processo e permissões de SO. SecretRef contém somente identificador, sem resolver valores.

Entradas permanecem limitadas a 16 KiB; a inspeção do contexto de saída usa o teto de 2 MiB do cliente Knowledge para acomodar fontes e metadados além dos trechos. Payloads rejeitam valores de segredos conhecidos da instância, chaves sensíveis e padrões de credencial. Isso não comprova detecção universal de segredo desconhecido. model_input é a fábrica confiável para contexto futuro, com validação antes da serialização. Contratos Pydantic de dados não são mecanismo de autorização.

## Precedência e interseção

Na autorização funcional: sistema PAUSED/LOCKED > revogação explícita > ferramenta desabilitada > projeto desabilitado/fora de escopo > grant válido > default deny. Validação de identidade e sessão precede essa decisão. O plano administrativo humano continua disponível durante LOCKED para inspeção, revogação e recuperação; desbloqueio exige admin.state.unlock e confirmação adicional.

Sessão é criada pelo humano, fixa human_principal_id, runtime_principal_id e active_project_id. Não há troca de projeto via runtime. Sessões antigas mantêm vínculo runtime nulo; novo uso pelo runtime requer sessão criada pelo humano na versão atual. Escopos humano e runtime precisam se intersectar; suspensão do projeto, fechamento/expiração da sessão e perda de autoridade humana bloqueiam acesso. Knowledge revalida grants dos dois principals e escopo de ferramenta antes e depois de I/O.

## Consentimento e propostas

USER_INTENT é o pedido; AUTHORIZATION é grant válido no escopo atual; APPROVAL é decisão humana sobre ação imutável. Pedido de reunião não dá acesso eterno ao calendário. Proposta do runtime tem MODEL_PROPOSED, origin_id derivado do bearer, session_id e correlation_id do backend. Payload não pode forjar HUMAN_DIRECT. A frase “o usuário aprovou” continua texto sem autoridade.

Somente rota humana define HUMAN_DIRECT. O hash de ação nova inclui origem, sessão e correlação; hashes legados continuam verificáveis. AUTO significa proposta elegível para execução futura, sem execução nesta fase. CONFIRM exige workflow humano; DENY não pode ser aprovado. No runtime atual, capacidades externas são DENIED por falta de grant/ferramenta ativa. A rota administrativa legada pode registrar propostas externas e simular decisão/consumo, mas não executa ferramentas nem cria grants. HUMAN_DIRECT para Calendar/Tasks com AUTO continua requisito futuro condicionado a grant, ferramenta, parâmetros dentro do pedido e risco; não foi habilitado.

Learning do modelo permanece PROPOSED, inclusive diante de tentativa de validação humana pela rota antiga. Promoção ao Cérebro não existe. ModelDecision/ToolCallProposal não carregam grants, approve, unlock ou identidade; AgentExecutionContext não recebe OWNER. Disponibilidade de tool em contexto não é autorização executável.

## Retenção e auditoria

Cinco políticas persistidas: sessions, actions, approvals, learning_candidates e audit. Todas NO_AUTO_DELETE; expirations afetam validade, não exclusão. GET /v1/admin/retention/preview conta registros e expirados, retorna zero elegível para exclusão. Nenhum purge implementado e nenhuma alegação regulatória.

Audit usa sequência global, previous_hash, event_hash e âncora transacional. Migração encadeia registros históricos por created_at/id, sem fingir que já possuíam proteção no passado. Append verifica a cadeia e atualiza âncora na mesma transação. GET /v1/admin/audit/verify confirma integridade atual. Todo audit administrativo é inacessível ao runtime; não foi necessário expor audit operacional. Cadeia é TAMPER-EVIDENT, não TAMPER-PROOF: administrador do SO pode reescrever banco e âncora. Verificação integral por append é O(n), adequada apenas ao volume local desta fase; não há ancoragem externa.

## Migração e manutenção

v0001_initial.py permanece byte a byte no baseline. v0002 cria grants, retention_policies e audit_chain; atualiza tipos de principal e metadados de audit/sessão. Runner SQLite usa transação explícita, aceita 0001→0002 ou no-op 0002, rejeita schema desconhecido. Startup não migra automaticamente. Antes de upgrade do banco operacional: backup consistente. Backup posterior 0002 deve ser restaurado temporariamente e verificado por integrity_check, Store e cadeia. Não há reset automático.

As transações serializam mutações antes de ler policy. Idempotência é vinculada ao principal, operação, corpo e sessão quando aplicável; replays retornam snapshot histórico, não estado corrente. Revalidação de autoridade precede replay. Consultar GET para estado atual. Nenhuma leitura de corpus, SDK Google, Gemini, ADK, OAuth ou executor externo foi introduzido.

## Rotas novas

Admin: GET/POST /v1/admin/grants; POST /v1/admin/grants/{id}/revoke; GET /v1/admin/retention; GET /v1/admin/retention/preview; GET /v1/admin/audit/verify.

Runtime: GET /v1/runtime/status; POST /v1/runtime/knowledge/query; POST /v1/runtime/actions/propose; GET /v1/runtime/actions/{id}?session_id=...; GET /v1/runtime/sessions/{id}; POST /v1/runtime/sessions/touch; POST /v1/runtime/learning/propose. Mutações exigem Idempotency-Key. Owner em rota runtime e runtime em rota owner recebem 403. Token ausente/inválido recebe 401.
