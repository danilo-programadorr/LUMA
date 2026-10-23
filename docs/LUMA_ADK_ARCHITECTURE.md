# ADK subordinado ao control plane

2026-10-23. Responsável: Codex. Candidata 0.5.0rc1; não é aprovação da 7E.

HUMAN_OWNER → Control Plane → grants/policies/revogação → Orchestrator → processo ADK → custom LumaAdkLlm → protocolo IPC → ModelProvider existente → worker Gemini → ModelDecision validado. ADK nunca recebe credencial, DB URL, Store, corpus ou executor. Somente SYSTEMROOT/WINDIR são herdados. Não há cliente Gemini novo nem Gemini Agent por string; todos os Agent usam BaseLlm próprio. O SDK transitivo no ambiente ADK não é usado para gerar.

ADK estável 2.12.0 em runtime/adk-venv, separado do .venv da API por incompatibilidade de dependências, documentada em reports/FASE_7E_DEPENDENCIES.md. Ambos usam google-genai 2.32.0. Pip check nos dois ambientes. Backend mantém seu lock anterior. A API não importa ADK; adk_bridge é a única nova fronteira subprocess. Processo sob o mesmo usuário do SO: não é sandbox completa contra código comprometido.

Workflow oficial é um grafo limitado, root luma. Product→Development e QA→Security são sequências; Growth/Content usa fan-out com JoinNode e fan-in. Concorrência do grafo fixada em 1 inicialmente, portanto o fan-out não promete paralelismo temporal. Sem loops emergentes nem transferências entre especialistas. Backend valida cada papel antes da chamada. MAX_AGENT_HOPS=5, MAX_AGENT_INVOCATIONS=6, duração 180s, chamadas Gemini limitadas pela configuração já aprovada. Budget acumulado: input 60000 e output+thought reportado 32768. Medição ocorre após resposta; tokens não reportados não podem ser contabilizados e não são presumidos zero. Nenhum billing.

Uma sessão mínima por invocação reaproveita ConversationService e seus checks antes/depois de gerar, Knowledge HTTP, citações e prevenção de alegação de execução. Resultados intermediários são dados não confiáveis limitados; não passam contextos completos entre papéis. Histórico ADK é efêmero; tarefas, workflows, resultados estruturados e auditoria são duráveis na LUMA. Não se persiste chain-of-thought. Falha de processo pode deixar tarefa RUNNING como evidência interrompida; não há replay automático de modelo nem promessa de retomada transparente de inferência. Jobs autorizados são independentes e recuperáveis.

Fontes: https://adk.dev/2.0/ ; https://adk.dev/graphs/ ; https://github.com/google/adk-python/tree/v2.12.0 . A interface BaseLlm é oficial. Não usamos web UI, ADK server ou confirmação ADK como autoridade.
