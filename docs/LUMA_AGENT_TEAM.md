# Equipe e contexto

2026-10-23, Codex. Nove papéis registrados no control plane: LUMA (root), Product, Development, Codex/Code Engineer, QA, Security, Data & Analytics, Growth & Marketing e Content & Social. Instruções individuais versionadas em backend/adk_worker/instructions; registry contém allowed_projects, capabilities, allowed_proposal_types, max_hops, model_profile e instruction_version.

Roteamento conservador determinístico do backend gera AgentRouteProposal. Não usa texto como autoridade. Papéis desconhecidos/desabilitados, duplicação e escopo divergente falham. O modelo não altera o grafo nem limites. Exemplo: segurança→Security; interface→Product; implementar→Product+Development; revisão→QA+Security; lançamento→Growth+Content; KPIs→Data. Mensagem desconhecida permanece LUMA. Codex é somente planejador, não executa CLI/shell. Security não concede acesso; QA não promove produção.

TaskAgentExecutionContext separa runtime principal, projeto, sessão mínima, correlation/task IDs, capabilities de proposta/leitura, deadline e hops. Contexto factual chega somente pela Knowledge API com as mesmas restrições da 7D. Mensagem atual é preservada; resultados anteriores são resumidos em tamanho e tratados como UNTRUSTED_DATA. O modelo pode produzir ModelDecision.proposed_actions: o backend valida parâmetros e cria candidato AGENT_PROPOSED em WAITING_AUTHORIZATION. Não cria autorização ou Job. Todas as ferramentas externas permanecem PLANNED/DISABLED.

AgentTask sobrevive à sessão por persistência; WorkflowRun contém papéis, status, uso, contagem, hashes e resultado mínimo. Não contém raciocínio privado. Os papéis podem analisar informações; nenhuma invocação atesta operação em produção.

## Propostas e conclusão da tarefa — correção dirigida 7E

O caminho /v1/tasks reutiliza validação e grounding da conversa, mas adia a persistência das propostas. Não grava os registros DENIED históricos da rota /v1/conversation/turn. Todos os ModelDecision dos especialistas e do root alimentam uma coleção interna de propostas; a síntese final não apaga uma proposta anterior válida. Validação final considera identidade de agente/runtime, projeto, grants atuais, registro/capability e parâmetros. O envelope exato deduplica propostas repetidas na mesma tarefa; risco e IDs pertencem ao backend.

ActionRequests, estado final de AgentTask, WorkflowRun, resposta idempotente e eventos de proposta são gravados juntos. Falha antes do commit remove todas as ações desta tarefa; o registro de falha preserva apenas diagnóstico seguro. Depois do commit, retry com a mesma chave e corpo devolve a resposta persistida sem nova geração ou ActionRequest. Exige ainda identidade, projeto e sessão humana válidos; uma sessão revogada não é reativada pelo retry.

WorkflowRun=COMPLETED significa fim do trabalho cognitivo. AgentTask=WAITING_AUTHORIZATION significa que há proposta aguardando decisão humana, sem manter processo de modelo aberto. Nenhuma Approval, ExecutionAuthorization ou Job é criada pelo agente. Uma ferramenta conhecida PLANNED/DISABLED pode receber proposta conforme a policy de candidatos existente; authorize/execute continuam exigindo ferramenta habilitada.

Telemetria: diagnostic no registro da tarefa e workflow contém estágios, contagens, booleanos e vocabulário fechado de erros. null significa não observado, não sucesso nem ausência de proposta. A observação do provider não altera o schema aceito, perfil de geração, BaseLlm ou grafo ADK.


### Modo de proposta explicita

ActionIntent e classificado pelo backend a partir da mensagem humana atual, nunca do Knowledge. ACTION_REQUEST/AMBIGUOUS selecionam LUMA_PROPOSAL -> SECURITY_REVIEW (dois agentes existentes). action_spec completo exige minItems=1; mensagens incompletas admitem ClarificationDecision e NEEDS_CLARIFICATION. Security emite recomendacao estruturada; approve_review nao e aprovacao humana. O acumulador estruturado mantem propostas de especialistas no fan-in dos demais grafos. workflow.model_call_diagnostics guarda apenas metadados sanitizados; proposal_state guarda IDs/hashes, nunca autoridade.
