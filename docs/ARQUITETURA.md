# Arquitetura LUMA — histórico 0.2.0 e evolução 0.3.0

Estado candidato vigente: [MODEL_LAYER_7D.md](MODEL_LAYER_7D.md), backend 0.4.0rc1 e schema 0003. Gemini real permanece BLOCKED_NEEDS_CREDENTIAL. A descrição abaixo preserva a arquitetura histórica 7B; evolução de confiança 7C em [TRUST_BOUNDARY_7C.md](TRUST_BOUNDARY_7C.md).

Data: 2026-10-21. Verificador: Codex. Status: implementação e testes locais; confiança alta para evidência relatada, produção não verificada. Histórico 0.1.0 preservado no commit baseline 7A `cb06235a3e7b53d097d4851d7cae34130e3c5b38`.

## Separação de responsabilidades

FastAPI/autenticação → principal persistido → project registry durável → capability/policy → cliente HTTP Knowledge → KnowledgeContext. Conteúdo é UNTRUSTED_DATA. LUMA não lê corpus/engine nem implementa ranking, ACL documental, freshness ou agentes. O harness de integração inicia o serviço Knowledge aprovado, fora do runtime LUMA, com bytecode externo desabilitado.

Configuração estática e segredos vêm de ambiente. Estado operacional vem exclusivamente do banco após bootstrap. Principal local é resolvido a cada autenticação pela identidade persistida, não por roles/capabilities enviados em payload. Capabilities administrativas explícitas são diferentes de knowledge.read e não dependem de `if OWNER: allow everything`.

## Persistência

SQLAlchemy 2.x Core com SQLite local, em `runtime/luma.db`. Repository encapsula SELECT/INSERT/UPDATE transacionais e paginação; regras de negócio não usam SQL exclusivo do SQLite. Configuração desta fase aceita apenas SQLite em runtime, enquanto futura migração PostgreSQL exigirá adaptador de configuração/migração validado. Não foi criado PostgreSQL.

Schema explícito v0001: principals, projects, tools, agents, system_state, actions, approvals, approval_requests, revocations, sessions, learning, audit_events, idempotency e schema_version. Cada entidade possui ID, colunas indexadas de principal/projeto, status, datas e snapshot JSON estruturado. Roles/scopes/capabilities são arrays auditáveis no principal; não existe alteração genérica de grants por HTTP. Contratos e transições ficam no domínio, não em campos livres do request.

Migração manual `python -m backend.migrate upgrade`: revision 0001 versionada, repetível sem duplicar, recusa schema desconhecido/parcial. Startup exige schema atual; não chama create_all nem reseta dados. Próximas mudanças exigem nova revisão explícita e testes; o runner ainda suporta só v0001. Não se afirma suporte operacional PostgreSQL já testado.

## Transações e concorrência

Toda mutação começa com UPDATE da linha de coordenação `schema_version.epoch`, antes das leituras de política. A trava de escrita do banco serializa mutações entre conexões/processos; não depende de lock Python. A mesma transação grava alteração, audit e idempotency. Transação de decisão grava approval/action/approval_request/audit; consumo grava consumed_at, action CANCELLED, approval_request/audit sem execução. Qualquer exceção reverte o conjunto.

As leituras de Knowledge verificam controle antes/depois de I/O; nenhuma revogação é substituída por um snapshot de autenticação antigo. Quando banco/audit falha, resposta fecha com erro. Auditoria HTTP adicional ocorre separadamente do audit atômico da mutação; se esse segundo registro falhar após commit, retry com a mesma chave recupera o resultado original sem repetir efeito.

GETs administrativos são paginados no SQL (até 100, offset até 10000), filtrados por principal/escopo. Eventos são append-oriented: Repository recusa UPDATE de audit/idempotency e não existe endpoint de edição. Acesso direto de administrador ao arquivo SQLite pode adulterar dados; não é ledger criptográfico ou proteção contra dono do SO.

## Runtime e limites

PAUSED/LOCKED bloqueiam Knowledge como em 7A, agora inclusive após restart. Tool state desabilitado/revogações não são reativados no bootstrap. Toda ferramenta externa permanece PLANNED/DISABLED; registry operacional e existência de executor são camadas separadas. Não há executor externo mesmo se um teste alterar diretamente um registro.

Sessões guardam somente metadados, expiram após 24h e podem ser encerradas. Candidatos persistem sem promoção canônica. Aprovações expiram após cinco minutos; prazo absoluto não é renovado no restart, consumo é único e estado atual prevalece. Backup usa mecanismo transacional SQLite; reset só manual, explícito, com aplicação parada e original arquivado.

Os módulos de memória da Fase7A permanecem como referências/fixtures de regressão e política conceitual; a aplicação não instancia esses stores. `Control`/`Store` são a autoridade operacional atual. Sem OAuth/MFA, múltiplos usuários provisionáveis, cifragem de DB, retention/rotação automática, pool de agentes, frontend, SDK Google ou SLA. Proteção do arquivo e backups depende das permissões locais do SO. Detalhes de endpoints e ameaças em CONTROL_PLANE_7B.md.
