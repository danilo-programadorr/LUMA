# Fase 7F-A — compatibilidade PostgreSQL local

Verificação: Codex, 2026-10-24. Candidata: Backend 0.6.0rc1.
Baseline preservado: 0.5.0, a2ec0c81f624b62bf3f8d8963188909be763060e.
Escopo: integração local de persistência. Não é aprovação de cloud nem da Fase 7F inteira.

## Instalação e origem

PostgreSQL 18.6, Windows x64, ZIP EDB indicado pela página oficial:
https://www.postgresql.org/download/windows/
https://www.enterprisedb.com/download-postgresql-binaries
Download: https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609
SHA-256 observado: e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2.
Este hash identifica o artefato recebido por HTTPS; não é assinatura publicada.
O executável postgres.exe retornou NotSigned na verificação Authenticode.
Não foi encontrado checksum separado na página de download consultada.
O teste SQL confirmou versão 18.6, arquitetura 64-bit e role luma_test.

Extraídos somente bin, lib, share e include em runtime/postgresql.
Não extraídos pgAdmin/StackBuilder; sem Docker, serviço Windows ou autostart.
Cluster runtime/postgresql-data, logs runtime/postgresql-logs.
UTF8, locale C, timezone UTC, checksums de páginas habilitados.
Bind 127.0.0.1, porta 55432 livre antes da inicialização.
pg_hba permite somente 127.0.0.1/32 com SCRAM-SHA-256.
Sem regra de firewall, túnel, LAN ou recurso cloud criado.

Senhas aleatórias de 32 bytes protegidas com DPAPI via Export-Clixml,
em runtime/postgresql-config com ACL somente usuário atual e SYSTEM.
Arquivo temporário de senha do initdb removido no finally.
Role administrativa luma_admin somente para setup e criação/cleanup dos bancos
temporários. Aplicação usa luma_test: LOGIN, NOSUPERUSER, NOCREATEDB,
NOCREATEROLE, NOREPLICATION. Banco dedicado luma_test; nenhuma cópia de SQLite.

## Alterações e auditoria SQL

- backend/app/database.py: seleção explícita de backend; SQLite permanece
  default e mantém restrição de caminho. PostgreSQL desta etapa aceita apenas
  psycopg, 127.0.0.1, role luma_test e bancos luma_test ou luma_test_*.
  Query parameters de URL são rejeitados. Isso NÃO é configuração cloud.
- backend/app/config.py: LUMA_DATABASE_BACKEND=postgresql opt-in; URL e senha
  não aparecem no repr de Settings. Não houve remoção das proteções locais.
- backend/app/control.py: propaga backend para Store.
- backend/migrate.py: SQLite mantém BEGIN IMMEDIATE. PostgreSQL usa transação
  DDL real e advisory transaction lock para serializar bootstrap.
- Migrações 0001–0004 permanecem byte-identical ao baseline Git, após
  normalização CRLF/LF. São executadas pela sequência original, não substituídas
  por metadata.create_all. Fresh, upgrades 1/2/3→4, execução repetida e rollback
  DDL são exercitados em bancos reais.
- SQLAlchemy não foi atualizado. Driver opcional separado:
  backend/requirements/postgres.txt, psycopg[binary] 3.3.6 e tzdata 2026.5.
  Lock de dependências validado da camada Gemini permanece intacto.
- Pesquisa em app/migrations/runner não encontrou INSERT OR REPLACE/IGNORE,
  PRAGMA, sqlite_master, rowid, AUTOINCREMENT ou UPSERT específico. O comando
  SQLite específico restante é BEGIN IMMEDIATE, protegido pelo backend.
- JSON passa por tipos SQLAlchemy/psycopg. Testes verificam Unicode, booleanos,
  null, objetos aninhados e timestamps ISO com timezone. O schema histórico
  armazena datas em strings; não houve conversão silenciosa para TIMESTAMPTZ.
- Primary keys/unique constraints impedem duplicação de IDs. As referências de
  domínio históricas são verificadas pela política, não por ForeignKeys SQL.
  O teste de FK usa tabelas temporárias de teste e prova enforcement do servidor;
  NÃO afirma que o schema LUMA possui FKs declaradas. Adicioná-las exige migração
  específica futura e revisão dos dados.
- Pool limitado a 5, overflow 0, timeout 10s, pre-ping. PostgreSQL READ COMMITTED,
  timezone UTC, connect timeout 5s, statement timeout 15s, lock timeout 10s.
  Parâmetros SQL ocultados em erros do engine; Store conserva erros sanitizados.

## Concorrência e autoridade

Preservada a atualização de schema_version.epoch antes de qualquer leitura
de política em Store.transaction. No PostgreSQL o UPDATE adquire row lock;
uma transação concorrente aguarda e lê o estado confirmado após obter o lock.
Todos os caminhos de mutação passam por essa fronteira. Isso serializa claims,
idempotência, alterações de autoridade e append da cadeia de auditoria.

Não foi acrescentado SKIP LOCKED: com a cadeia global de auditoria e os dados
de autoridade compartilhados, introduzir apenas lock de job enfraqueceria a
fronteira existente sem benefício nesta etapa. A escolha é correção por
serialização global, com limitação de throughput explicitamente aceita para
validação local; não é benchmark de escala cloud.

Testes usam dois threads sincronizados por barreira, conexões reais distintas,
um job elegível e exigem um único claim/efeito. Também verificam mesma chave
idempotente, updates concorrentes e append concorrente da cadeia.
Falha injetada durante autorização reverte aprovação/autorização/action/audit.
Falha ao criar job não deixa job parcial; a autorização previamente confirmada
continua válida. Aprovação e autorização são atômicas; criação posterior do job
é transação separada deliberada, sem execução automática implícita.

Crash após claim permite reclaim ao expirar lease, invalidando worker antigo.
Crash após efeito sandbox confirmado exige reconciliação e gera um único
ExecutionRecord. Isso comprova persistência real com efeito SANDBOX; não houve
execução Codex/ferramenta externa, nem alegação de exactly-once externo.

## Reprodução

Na raiz D:/projetos/luma, PowerShell 7:
1. Instalar driver com ./.venv/Scripts/python.exe -m pip install -r backend/requirements/postgres.txt
2. Executar ./scripts/setup_postgres_local.ps1 em ambiente novo.
3. Executar ./scripts/start_postgres_local.ps1 e ./scripts/check_postgres_local.ps1.
4. Executar ./scripts/test_postgres_local.ps1.
5. Executar ./scripts/stop_postgres_local.ps1.

Setup verifica artefato/versão, recusa cluster parcial e não sobrescreve dados.
O hash fixado é o observado nesta rodada, não uma prova independente de publisher.
A instalação inicial foi realizada por comandos equivalentes; o script de setup
foi verificado por parser PowerShell e pelo caminho idempotente no cluster atual.
Não se afirma uma segunda instalação limpa pelo script consolidado.

Testes temporários usam luma_test_<uuid> e DROP somente desses bancos em teardown.
O banco persistente de desenvolvimento permanece. Nenhum teste requer banco
público ou senha no Git. Erros de download/UAC exigem parada, sem fallback informal.

## Evidência e limites

Resultados em FASE_7F_POSTGRES_REAL.json, FASE_7F_POSTGRES_TESTES.xml,
FASE_7F_TESTES.xml e FASE_7F_AUDITORIA.json. A primeira tentativa de coleta teve
erro de encoding no arquivo novo; corrigido para UTF-8 antes dos testes reais.
A validação de restart parou/iniciou o cluster e confirmou um marcador persistido
e a cadeia de auditoria; o marcador foi removido depois.

Auditoria 7F reutiliza os controles 7E, alterando somente a branch autorizada e
a exigência de remote para a URL exata configurada pelo proprietário.
Também compara as quatro migrações com o baseline preflight.
Cérebro e Meu Gestor não foram alterados. Nenhum recurso cloud criado.

A separação completa de factories CONTROL_PLANE/LOCAL_RUNTIME continua pendente
do restante do 7F-A. Esta entrega valida PostgreSQL local; não ativa modo cloud,
Owner Auth, enrollment, canal outbound, Web ou Codex real. Próximo subgate
recomendado: concluir essa separação antes de 7F-B, mediante nova autorização.
