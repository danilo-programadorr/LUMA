# Fase 7E — ADK, execução durável e executor local

Data: 2026-10-23. Responsável: Codex. Baseline aprovado c461a8f69bddb6c2ead1cb21f69f3a17bd1d378f (0.4.0, 304 testes, Gemini 7D 8/8). Branch codex/fase-7e-adk-orchestration. Candidata 0.5.0rc1. Adendo Local PC Executor incorporado; arquitetura híbrida, sem integrações mutáveis novas.

## Dependências e fronteira

ADK estável 2.12.0 consultado antes da instalação. Fontes oficiais e conflito de dependências em FASE_7E_DEPENDENCIES.md. ADK requer OpenTelemetry<=1.42.1 e websockets<16, incompatíveis com o ambiente da API aprovado. Escolha: runtime/adk-venv isolado, lock completo adk-lock.txt, sem extras. Backend lock inalterado; google-genai 2.32.0 preservado nos dois ambientes. Pip check e imports passaram. ADK transitivo não configura servidor nem cliente Gemini direto.

Implementado custom BaseLlm que pede geração ao host por IPC limitado. Backend constrói contexto, valida identidade/projeto/grants, executa ConversationService/Knowledge HTTP, ModelProvider e worker Gemini existentes. Perfil CONVERSATIONAL low/32768 sem sampling permanece intacto, com JSON Schema e diagnóstico/uso. Nenhuma credencial ou DB é enviada ao processo ADK. O isolamento de processo não é sandbox de SO; ambos rodam sob o mesmo usuário.

## Orquestração

Nove papéis registrados com instruções individuais versionadas: LUMA root, Product, Development, Codex/Code Engineer (planejamento), QA, Security, Data, Growth e Content. Workflow oficial graph, sequências e fan-out/fan-in com JoinNode. Concorrência 1 inicialmente. Roteamento conservador do backend, não autoridade do modelo. Limites: 5 hops, 6 invocações, 180s, input 60000 e output+thought reportado 32768. Sem loops/transferências emergentes. Tokens indisponíveis não são presumidos conhecidos; budget agregado interrompe após contabilizar a resposta, não é hard cap de faturamento.

Contextos separados por sessão mínima de agente; só dados pertinentes e resultados intermediários limitados, nunca sessão ADK como fonte de autorização. Grounding/citações e filtros da 7D reaproveitados. AgentTask/WorkflowRun e resultados estruturados/hashes persistem; não se salva chain-of-thought. Os jobs podem executar sem sessão. Inferências interrompidas por crash não têm replay automático; registro RUNNING precisa revisão, preservando ausência de cobrança/retry cego.

## Autorizações e jobs

Migração 0004 aditiva; arquivos 0001–0003 inalterados. SERVICE_EXECUTOR separado, capability mínima. Runtime/modelo/agentes não podem criar aprovação humana. ActionRequest→Approval→ExecutionAuthorization→Job→ExecutionRecord. Risco definitivo pelo backend; HIGH exige one-shot exato, step-up e <=10 minutos; CRITICAL unattended negado. ONE_SHOT, BOUNDED_WINDOW e RECURRING_POLICY com template exato, prazo/quota e policy_version. Sem wildcard expansivo. Envelope inclui recursos/destino, parâmetros, janela e execution target/device. Revogação/kill switch/grants/tool/projeto são revalidados antes do efeito.

Scheduler e executor são processos separados. Estados, lease atômico 30s, recuperação, idempotência derivada no servidor, quota reservada e ledger/reconciliation. Sandbox effect é local/transacional; não se alega exactly-once universal nem idempotência de APIs externas. UNKNOWN exige revisão, não repetir efeito às cegas. Recurring cria ocorrências dentro do template/prazo/quota; CONDITION é interface interna sem fonte externa. Atraso: SKIP por padrão, graça explícita ou reautorização.

## Adendo local

ExecutionTarget CLOUD/LOCAL_DEVICE/EITHER; LOCAL_DEVICE fixa device_id, sem fallback silencioso. Device registry com digest de credencial de desenvolvimento, heartbeat/capability check, TTL 60s e revogação. PC offline→WAITING_FOR_DEVICE; retorno exige validação atual. Modelo não amplia paths nem capabilities. Codex, filesystem, Git write, browser e desktop permanecem PLANNED/DISABLED.

Cliente local inicia outbound autenticado heartbeat/poll, HTTPS fora de loopback, sem listener/RDP/porta pública. Canal não substitui fila. Produção não instala TestTool: a execução física sandbox é exclusiva dos harnesses em processos separados com DB local; o canal HTTP de dispositivo é validado separadamente. Não se afirma integração mutável remota ou cloud operacional. Enrollment/rotação hardened e Windows Service ficam para etapa futura. PC ligado ainda é necessário.

## Evidências e limites

Testes dirigidos aprovados: execução (22), ADK/orquestração (19), device/jobs (20), subprocess owner-offline/restart (2). São subconjuntos, não devem ser somados ao total final como execuções distintas. Dois testes históricos tiveram contagens atualizadas para três principals e 15 categorias de retenção; backup passa a esperar schema 4. Teste de upgrade v2 exclui tabelas ainda inexistentes no snapshot anterior e espera grants/retention aditivos da 0004. Nenhum teste anterior foi removido e nenhum check de segurança relaxado.

Dataset básico backend/tests/luma_7e.evalset.json validado pelo EvalSet oficial (6 casos). Dataset determinístico complementar documenta agentes esperados e proibições. Não foi executado juiz LLM; policy tests são autoridade para segurança. Registros reais de subprocessos: FASE_7E_OFFLINE_EXECUTION.json e FASE_7E_RESTART_REAL.json, com um efeito/um ExecutionRecord, sessões encerradas, task/auth persistidas e cadeia de auditoria verificada. Nenhum owner token no executor.

Validação ADK+Gemini: BLOCKED_NEEDS_CREDENTIAL neste processo, zero casos reais 7E. O sucesso real 7D não é prova de integração ADK. backend.validate_adk prepara dez casos autorizados e para na primeira falha; sem efeito externo. Executar no PowerShell já configurado: .\.venv\Scripts\python.exe -m backend.validate_adk. Enviar somente FASE_7E_ADK_REAL.json sanitizado. Não é necessária credencial nova.

Decisão vigente: NO-GO para promoção 0.5.0 até a rodada real 7E passar e ser revisada. Sem 7F/deploy/recursos pagos, Calendar/Tasks/Gmail/Codex real, browser/desktop automation, frontend/voz/billing/multi-tenant. Arquitetura recomendada para 7F: Cloud Run Control Plane + runtime ADK separado + Cloud SQL/PostgreSQL + Secret Manager + Cloud Scheduler/Tasks e Local PC Executor outbound. Agent Runtime é alternativa a avaliar, não control plane. Comparação e limitações em LUMA_ALWAYS_ON_ARCHITECTURE.md e FASE_7E_DEPLOYMENT_READINESS.md. Decisão arquitetural é inferência técnica documentada, não prova de operação cloud.

## Fechamento verificável da candidata

Auditoria local VERIFIED, sem erros: 203 hashes de entregas do Cérebro e 763 arquivos da fonte preservados; HEAD da fonte e do repositório financeiro 9fe7fd3a69a537f9e67953b7028e64c676a48547, árvores destes repositórios limpas. Scanner por padrões não é prova universal de ausência de secrets. Evidência Gemini 7D preservada, SHA256 7854afe181568e34a8515ddcc2a56c2121ecb2a5456649fc4dcc16cf210c05f0. Pip check aprovado nos dois ambientes.

A primeira suíte (364 aprovados, uma falha de expectativa na migração v2) foi preservada em FASE_7E_TESTES_INICIAL.txt/xml. A correção e os ajustes finais passaram em 42 testes dirigidos. O resultado definitivo fica em FASE_7E_TESTES.txt/xml. O campo latency_ms nos relatórios de subprocessos mede a inspeção final do estado, não a latência completa do scheduler/executor.

Status CONFIRMADO, confiança ALTA para os testes locais e hashes verificados em 2026-10-23 por Codex. Operação cloud e integração real ADK+Gemini permanecem NÃO CONFIRMADAS. Commit da candidata e hashes finais serão registrados no recibo local runtime/phase-7e-candidate-receipt.json, fora do versionamento para evitar autorreferência.

Resultado consolidado final: **367 testes distintos aprovados**, zero falhas e zero casos sem execução. A suíte principal registrou 366 aprovados + um skip em 262,29s; o skip ocorreu por ausência de LUMA_TEST_KNOWLEDGE_WORKSPACE. Esse mesmo caso foi executado separadamente com a variável configurada e passou em 23,62s, conforme FASE_7E_KNOWLEDGE_HTTP.txt/xml. Os dois JUnit foram comparados por classname/name para confirmar cobertura exata dos 367 casos. Um aviso de depreciação Starlette/httpx permanece; não se alterou o lock aprovado para tratá-lo nesta fase.
