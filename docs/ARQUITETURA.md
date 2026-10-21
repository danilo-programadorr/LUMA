# Arquitetura LUMA — histórico 0.2.0 e evolução 0.3.0

Data: 2026-10-21. Verificador: Codex. Status: implementaÃ§Ã£o e testes locais; confianÃ§a alta para evidÃªncia relatada, produÃ§Ã£o nÃ£o verificada. HistÃ³rico 0.1.0 preservado no commit baseline 7A `cb06235a3e7b53d097d4851d7cae34130e3c5b38`.

## SeparaÃ§Ã£o de responsabilidades

FastAPI/autenticaÃ§Ã£o â†’ principal persistido â†’ project registry durÃ¡vel â†’ capability/policy â†’ cliente HTTP Knowledge â†’ KnowledgeContext. ConteÃºdo Ã© UNTRUSTED_DATA. LUMA nÃ£o lÃª corpus/engine nem implementa ranking, ACL documental, freshness ou agentes. O harness de integraÃ§Ã£o inicia o serviÃ§o Knowledge aprovado, fora do runtime LUMA, com bytecode externo desabilitado.

ConfiguraÃ§Ã£o estÃ¡tica e segredos vÃªm de ambiente. Estado operacional vem exclusivamente do banco apÃ³s bootstrap. Principal local Ã© resolvido a cada autenticaÃ§Ã£o pela identidade persistida, nÃ£o por roles/capabilities enviados em payload. Capabilities administrativas explÃ­citas sÃ£o diferentes de knowledge.read e nÃ£o dependem de `if OWNER: allow everything`.

## PersistÃªncia

SQLAlchemy 2.x Core com SQLite local, em `runtime/luma.db`. Repository encapsula SELECT/INSERT/UPDATE transacionais e paginaÃ§Ã£o; regras de negÃ³cio nÃ£o usam SQL exclusivo do SQLite. ConfiguraÃ§Ã£o desta fase aceita apenas SQLite em runtime, enquanto futura migraÃ§Ã£o PostgreSQL exigirÃ¡ adaptador de configuraÃ§Ã£o/migraÃ§Ã£o validado. NÃ£o foi criado PostgreSQL.

Schema explÃ­cito v0001: principals, projects, tools, agents, system_state, actions, approvals, approval_requests, revocations, sessions, learning, audit_events, idempotency e schema_version. Cada entidade possui ID, colunas indexadas de principal/projeto, status, datas e snapshot JSON estruturado. Roles/scopes/capabilities sÃ£o arrays auditÃ¡veis no principal; nÃ£o existe alteraÃ§Ã£o genÃ©rica de grants por HTTP. Contratos e transiÃ§Ãµes ficam no domÃ­nio, nÃ£o em campos livres do request.

MigraÃ§Ã£o manual `python -m backend.migrate upgrade`: revision 0001 versionada, repetÃ­vel sem duplicar, recusa schema desconhecido/parcial. Startup exige schema atual; nÃ£o chama create_all nem reseta dados. PrÃ³ximas mudanÃ§as exigem nova revisÃ£o explÃ­cita e testes; o runner ainda suporta sÃ³ v0001. NÃ£o se afirma suporte operacional PostgreSQL jÃ¡ testado.

## TransaÃ§Ãµes e concorrÃªncia

Toda mutaÃ§Ã£o comeÃ§a com UPDATE da linha de coordenaÃ§Ã£o `schema_version.epoch`, antes das leituras de polÃ­tica. A trava de escrita do banco serializa mutaÃ§Ãµes entre conexÃµes/processos; nÃ£o depende de lock Python. A mesma transaÃ§Ã£o grava alteraÃ§Ã£o, audit e idempotency. TransaÃ§Ã£o de decisÃ£o grava approval/action/approval_request/audit; consumo grava consumed_at, action CANCELLED, approval_request/audit sem execuÃ§Ã£o. Qualquer exceÃ§Ã£o reverte o conjunto.

As leituras de Knowledge verificam controle antes/depois de I/O; nenhuma revogaÃ§Ã£o Ã© substituÃ­da por um snapshot de autenticaÃ§Ã£o antigo. Quando banco/audit falha, resposta fecha com erro. Auditoria HTTP adicional ocorre separadamente do audit atÃ´mico da mutaÃ§Ã£o; se esse segundo registro falhar apÃ³s commit, retry com a mesma chave recupera o resultado original sem repetir efeito.

GETs administrativos sÃ£o paginados no SQL (atÃ© 100, offset atÃ© 10000), filtrados por principal/escopo. Eventos sÃ£o append-oriented: Repository recusa UPDATE de audit/idempotency e nÃ£o existe endpoint de ediÃ§Ã£o. Acesso direto de administrador ao arquivo SQLite pode adulterar dados; nÃ£o Ã© ledger criptogrÃ¡fico ou proteÃ§Ã£o contra dono do SO.

## Runtime e limites

PAUSED/LOCKED bloqueiam Knowledge como em 7A, agora inclusive apÃ³s restart. Tool state desabilitado/revogaÃ§Ãµes nÃ£o sÃ£o reativados no bootstrap. Toda ferramenta externa permanece PLANNED/DISABLED; registry operacional e existÃªncia de executor sÃ£o camadas separadas. NÃ£o hÃ¡ executor externo mesmo se um teste alterar diretamente um registro.

SessÃµes guardam somente metadados, expiram apÃ³s 24h e podem ser encerradas. Candidatos persistem sem promoÃ§Ã£o canÃ´nica. AprovaÃ§Ãµes expiram apÃ³s cinco minutos; prazo absoluto nÃ£o Ã© renovado no restart, consumo Ã© Ãºnico e estado atual prevalece. Backup usa mecanismo transacional SQLite; reset sÃ³ manual, explÃ­cito, com aplicaÃ§Ã£o parada e original arquivado.

Os mÃ³dulos de memÃ³ria da Fase7A permanecem como referÃªncias/fixtures de regressÃ£o e polÃ­tica conceitual; a aplicaÃ§Ã£o nÃ£o instancia esses stores. `Control`/`Store` sÃ£o a autoridade operacional atual. Sem OAuth/MFA, mÃºltiplos usuÃ¡rios provisionÃ¡veis, cifragem de DB, retention/rotaÃ§Ã£o automÃ¡tica, pool de agentes, frontend, SDK Google ou SLA. ProteÃ§Ã£o do arquivo e backups depende das permissÃµes locais do SO. Detalhes de endpoints e ameaÃ§as em CONTROL_PLANE_7B.md.
