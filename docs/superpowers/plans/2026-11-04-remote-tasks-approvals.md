# 7F-D-B — plano de execução local

Spec: autorização do Owner em attachments/291fcd9b-0e51-431d-ac65-35eff5cbac9a/Texto colado.txt.
Arquitetura aprovada: integrar RemoteTask à autoridade e execução 7E; sem pipeline paralelo.
Execução inline; nenhum commit, push, merge ou deploy.

- [x] Contratos estritos e gateway Owner persistente em agent_tasks existente; tipos, idempotência, TTL e consulta paginada.
- [x] Snapshot/digest e decisão transacional única; reutilizar candidate/authorize/job/revoke da 7E na mesma transação. Rejeição, cancelamento e revogação canônicos.
- [x] Rotas Owner com recent-auth; projeção sem material executável; runtime sem poder de aprovação. Limites e auditoria.
- [x] UI Tasks/Approvals reais com detalhes, rejeição, cancelamento, revogação, estados e recuperação de rede; links internos e mobile.
- [x] Testes backend e PostgreSQL de persistência/concorrência/offline/revogação, frontend e browser emulado. Reutilizar baseline, contar somente IDs únicos.
- [x] Auditoria/secret scan/integridade, documentação e gate de aceitação real do Owner.

Riscos de revisão: decisão concorrente; mutação da proposta; cancelamento concorrente; expiração offline; dados de outro Owner/projeto; resultado tardio; nenhuma autoridade no frontend.
Biblioteca suspensa. Nenhuma chamada paga. TestTool apenas; Codex, shell operacional, filesystem operacional, browser/desktop executores desabilitados.


## Ledger de execução
- RED inicial: módulo remote_tasks ausente. GREEN inicial: 5 cenários.
- RED HTTP: rota ausente. GREEN: Owner com binding e proposta exata.
- PostgreSQL real: 5 novos testes de concorrência/persistência passaram; regressão completa 86 PASS.
- Revisão independente identificou integração analítica ausente, filtro anterior à paginação, estado histórico após revoke, operações incompatíveis na UI e grant de rejeição. Correções em implementação/verificação.
- Ruling: schema 8 e tabela JSON agent_tasks existentes suportam o wrapper; nenhuma migration 1–8 será editada e nenhuma migration redundante será criada.
- Ruling: UI operacional expõe apenas TestTool record; HIGH/CRITICAL são cenários de policy em testes, sem novos executores.
- Ruling: tarefas analíticas com computador usam envelope e sessão do RuntimeTaskService; sem computador pedem esclarecimento. Rotas runtime usam SERVICE_RUNTIME, nunca Owner/device credential. Não iniciar modelo real/chamada paga nesta fase.
- Regressão backend completa e browser estão em execução. Não contar reruns como novos casos.

Fechamento local: 1086 IDs únicos verdes, 1043 baseline preservados; auditoria VERIFIED, secret scan PASSED. Control Plane local reiniciado com schema 8 atual, sem migration. Aceitação real Owner segue pendente. Nenhum commit/push/deploy.

Fechamento: 7F-D-B_REMOTE_TASKS_APPROVALS_VALIDATED; 1093 IDs únicos PASS, Owner approve/efeito único/reject/cancel/revoke reais confirmados, retorno assinado bloqueado após revoke e reinício real preservando estados. Nenhuma fase futura iniciada.
