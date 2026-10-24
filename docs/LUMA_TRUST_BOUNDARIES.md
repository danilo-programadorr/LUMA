# Fronteiras de confiança — 7F-A2

Data 2026-10-24; verificador Codex; candidata 0.6.0rc1.

USER_INTENT ≠ PROPOSAL ≠ APPROVAL ≠ EXECUTION_AUTHORIZATION ≠ JOB ≠ EXECUTION.

1. HUMAN_OWNER autentica no Control Plane local. SERVICE_RUNTIME não pode usar
   as rotas administrativas, conceder grant, desbloquear estado ou autorizar ação.
2. Control Plane não carrega adapters de inteligência e não exige secrets deles.
3. Runtime não recebe credenciais Owner/DB; startup recusa tais variáveis.
   Configuração Gemini/Knowledge é local, não transmitida nos envelopes.
4. RuntimeProposal é dado não confiável. Revalidação usa estado atual do banco,
   independentemente de snapshots, review, risk hint ou histórico.
5. SERVICE_EXECUTOR permanece principal diferente de SERVICE_RUNTIME.
   Jobs, leases e reconciliação existentes permanecem, sem ativação de Codex.
6. Entradas e resultados JSON são limitados, extra fields proibidos e versionados.
   Replay idêntico é idempotente; replay divergente, cancelado ou expirado não
   reativa tarefa. Identidade/dispositivo incorreto não muda o estado de vítima.
7. Auditoria canônica registra eventos e IDs, não corpo de prompts, respostas,
   tokens ou raciocínio privado. Task/result persistidos contêm somente o contrato
   limitado; não são log de CoT.
8. PostgreSQL é local e isolado, SCRAM em 127.0.0.1:55432. Senhas DPAPI ignoradas.
   Não houve API cloud, firewall, túnel, Owner Auth público ou device enrollment.

Testes adversariais cobrem owner/projeto/tool/workspace/resource/destination
forjados, downgrade de risco, campos de autorização, kill switch, revogação,
resultados duplicados/expirados/cancelados e credenciais proibidas no runtime.
Separação de aplicação não impede um administrador do sistema operacional de
ler processos; identidade criptográfica e isolamento de deployment pertencem
aos gates futuros e não são declarados validados aqui.
