# Fase 7F-A2 — separação Control Plane / Local Runtime

Data: 2026-10-24. Verificador: Codex.
Candidata: 0.6.0rc1. Baseline: 274625090afb3c9749ffe26c9f82e33eaf728dc6.
Resultado: 7F-A2_CONTROL_RUNTIME_SPLIT_VALIDATED.
Esta aprovação é do subgate local A2; a Fase 7F completa permanece em andamento.

## Resultado implementado

Factories distintas por LUMA_MODE, com rejeição de valor desconhecido.
CONTROL_PLANE inicializa sem Gemini/ADK/Knowledge/Codex, mantém banco e política
canônicos, autenticação Owner local e serviços existentes de aprovação,
autorizações, jobs, devices e auditoria.
LOCAL_RUNTIME não importa o banco canônico nem serviços administrativos, recusa
credenciais Owner/admin/DB e expõe somente health local. RuntimeTaskProcessor,
IntelligenceHandler, adaptadores locais Gemini/Knowledge e bridge ADK compõem
a inteligência. SERVICE_RUNTIME e SERVICE_EXECUTOR permanecem separados.

O gateway usa contratos JSON versionados e limitados. Sessão, projeto, runtime,
device, validade, registry e escopo são vinculados pelo Control Plane.
Resultados são revalidados contra estado atual, inclusive grants Knowledge,
revogação, cancelamento e kill switch. O risco efetivo é canônico.
Proposta aceita cria somente ActionRequest WAITING_AUTHORIZATION; nenhuma
aprovação, ExecutionAuthorization ou Job é criada por resultado do runtime.

LOCAL_DEV conserva rotas e coordenadores históricos, com chamadas de modelo
atravessando os mesmos envelopes e RuntimeTaskProcessor. Política de propostas,
migrations e serviços de autoridade foram reutilizados.
O runtime separado usa ANALYZE; a compatibilidade integrada usa MODEL_GENERATION.
Control Plane separado rejeita MODEL_RESULT, mantendo contexto Knowledge local.

## Evidência executada

- 523 testes locais finais aprovados: todos os 459 baseline e 64 novos.
- 47 testes PostgreSQL real aprovados: todos os 43 baseline e 4 novos.
- Total único: 570. Incremento sobre baseline 502: 68.
- A execução específica final dos 64 testes de fronteira também passou.
  Ela não é somada novamente ao total.
- PostgreSQL 18.6 local, SCRAM, 127.0.0.1:55432; encerrado depois dos testes.
- Processos limpos provam imports e startup sem dependências proibidas.
- ADK 2.12.0 local executou com modelo sintético, sem credenciais de DB/Owner
  e sem chamada Gemini real. SDKs/modelo configurado não foram atualizados.
- Protocol round-trip, snapshot schema, rejeição de versão, payload limits,
  idempotência/retry e ataques de identidade/escopo/risco foram exercitados.
- PostgreSQL: resultado concorrente gera uma ActionRequest; retry após recriar
  serviço retorna resposta persistida; cancelamento não é revertido.
- Audit chain VERIFIED; auditoria de fontes/migrations/imports VERIFIED.
  Cérebro, Meu Gestor e migrations 0001–0004 preservados.

Relatórios finais: FASE_7F_A2_FINAL_TESTES.xml,
FASE_7F_A2_BOUNDARY_FINAL_TESTES.xml, FASE_7F_A2_POSTGRES_TESTES.xml,
FASE_7F_A2_AUDITORIA.json e FASE_7F_CONTROL_RUNTIME_BOUNDARY.json.

## Correções durante a rodada

A primeira verificação de compatibilidade detectou serialização indevida de
sessões distintas. O cache agora coordena somente tarefas iguais; 96 casos de
compatibilidade tinham 95 passes e uma falha antes da correção.
A primeira suíte ampla tinha 507 passes e uma falha de classificação:
MODEL_INVALID_RESPONSE substituía PROPOSAL_SCHEMA_INVALID. O transporte passou
a preservar a classificação histórica. Os 39 testes de proposal_flow passaram
após o ajuste e a suíte completa foi repetida com sucesso.
FASE_7F_A2_TESTES.* preserva essa execução diagnóstica, não o resultado final.
Os últimos ajustes de erro de domínio HTTP foram exercitados pela suíte final
de fronteira; não houve mudança de lógica PostgreSQL para esse mapeamento.
Uma chamada de ferramenta não foi executada por indisponibilidade da revisão
automática de aprovação; após continuação do proprietário o fluxo normal foi
retomado sem contornar o mecanismo.

## Limites e riscos restantes

- Nenhum endpoint de task/result remoto foi exposto. O binding de device é uma
  interface interna confiável; assinatura/enrollment/polling pertencem a 7F-C.
- Owner Auth ainda é local, não Google/Identity Platform. Não houve frontend,
  URL pública, Cloud Run, Cloud SQL ou recurso cloud criado.
- Runtime cache é limitado e em memória. Restart pode repetir análise/modelo;
  o Control Plane deduplica o efeito lógico duravelmente.
- Separação de aplicação não equivale a sandbox de código Python malicioso ou
  proteção contra administrador do sistema operacional.
- Não houve Codex real nem execução externa. Lease/job/reconciliação baseline
  permanecem preservados; testes de efeitos continuam sandbox.
- O futuro adapter de workspace/Codex deverá bindar caminho autorizado à
  autorização executável; esta etapa apenas valida IDs de escopo e não habilita
  ferramentas de filesystem.
- A advertência de depreciação Starlette/httpx permanece; não motivou atualização
  de dependências fora do escopo.
- Sem deploy ou phone acceptance. Não declarar 7F inteira GO.

Próximo gate recomendado: 7F-B — LUMA Web + Owner Authentication.
Não iniciado. Exige autorização do proprietário.
