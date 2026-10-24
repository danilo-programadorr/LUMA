# Fase 7F — preflight e lacunas do gate 7F-A

Data: 2026-10-24. Verificador: Codex.
Status: NO-GO PARA AVANÇAR, por pré-requisito de PostgreSQL real pendente.
Não representa falha de um teste PostgreSQL: nenhum foi executado.
Backend mantido em 0.5.0; Web não criado; candidata 0.6.0rc1 não iniciada.
Baseline 7E: 62b2afa074966c6a7c3886a2d2d4730cbce23442.
Branch local: codex/fase-7f-remote-control-local-executor.

## Evidência e confiança

| Achado | Fonte no baseline | Classificação |
| --- | --- | --- |
| Banco aceita apenas SQLite em runtime | backend/app/database.py, database_path e engine_for | Código inspecionado; alta confiança |
| Store exige arquivo local e schema versão 4 | backend/app/database.py, Store | Código inspecionado; alta confiança |
| Migração usa BEGIN IMMEDIATE | backend/migrate.py | Código inspecionado; alta confiança |
| Inicialização acopla modelo, Knowledge e orquestração | backend/app/main.py, create_app | Código inspecionado; alta confiança |
| Bootstrap atual usa identidade local | backend/app/control.py, bootstrap | Código inspecionado; alta confiança |
| Escrita serializada por atualização de schema_version.epoch | backend/app/database.py, Store | Código inspecionado; não prova concorrência PostgreSQL |
| Codex instalado e autenticado via ChatGPT | codex --version, codex login status, codex exec --help | Verificação local nesta rodada; não equivale a execução real |
| 459 testes e auditoria VERIFIED | phase-status.json e reports/FASE_7E_RELEASE_* | Evidência histórica 7E; não rerodada em 7F |

## Trabalho necessário, após resolver pré-requisito

1. Separar factories CONTROL_PLANE e LOCAL_RUNTIME, com testes que impeçam
   carregamento de Gemini, Knowledge, ADK e ferramentas no processo cloud.
2. Preservar migrações 0001–0004; adicionar estratégia explícita de bootstrap
   PostgreSQL e engine/pooling apropriados, mantendo a restrição SQLite local.
3. Provar transações, concorrência, idempotência e cadeia de auditoria em
   PostgreSQL real. A serialização existente é hipótese de desenho, não prova.
4. Só depois avançar, em ordem, para 7F-B, C, D, E e F.
   Login da CLI não valida sandbox, ambiente de subprocesso ou worktree.

## Escopo efetivamente executado

Preflight somente leitura de ferramentas, código e metadados GCP; criação da
branch local e destes relatórios. Nenhum recurso cloud criado, API habilitada,
chave OpenAI usada, deploy, push ou chamada real Codex/Gemini.
Gemini/Knowledge permanecem na arquitetura local existente.
Nenhuma escrita foi feita no Cérebro ou no Meu Gestor nesta rodada.
Nenhuma migração ou evidência 7E foi modificada.
A auditoria completa 7F não foi executada; não reutilizar VERIFIED 7E como
aprovação desta fase. O auditor histórico verifica a branch 7E explicitamente;
uma auditoria 7F futura deverá manter controles e documentar a mudança de branch.

VALIDATED LOCALLY: descoberta de ferramentas, autenticação CLI e preflight GCP.
VALIDATED CLOUD: nenhum comportamento da aplicação.
VALIDATED ON REAL PHONE: não executado.
VALIDATED WITH REAL CODEX: não executado.

Autenticação Owner, enrollment, estados online/offline, canal outbound, tarefas,
aprovações, revogação, kill switch e restart 7F permanecem NÃO IMPLEMENTADOS/
NÃO TESTADOS. Não produzir relatórios PASSED para etapas não executadas.

## Próximo passo pendente

Resposta à escolha enviada ao proprietário: PostgreSQL isolado em runtime sem
serviço global, Docker Desktop configurado pelo proprietário, ou PostgreSQL de
testes existente. Não solicitar credenciais no chat.
A regra de parada é a seção 197 da autorização 7F: preservar evidência e não
contornar gates críticos. Não iniciar 7G.
