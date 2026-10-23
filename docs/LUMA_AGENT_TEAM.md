# Equipe e contexto

2026-10-23, Codex. Nove papéis registrados no control plane: LUMA (root), Product, Development, Codex/Code Engineer, QA, Security, Data & Analytics, Growth & Marketing e Content & Social. Instruções individuais versionadas em backend/adk_worker/instructions; registry contém allowed_projects, capabilities, allowed_proposal_types, max_hops, model_profile e instruction_version.

Roteamento conservador determinístico do backend gera AgentRouteProposal. Não usa texto como autoridade. Papéis desconhecidos/desabilitados, duplicação e escopo divergente falham. O modelo não altera o grafo nem limites. Exemplo: segurança→Security; interface→Product; implementar→Product+Development; revisão→QA+Security; lançamento→Growth+Content; KPIs→Data. Mensagem desconhecida permanece LUMA. Codex é somente planejador, não executa CLI/shell. Security não concede acesso; QA não promove produção.

TaskAgentExecutionContext separa runtime principal, projeto, sessão mínima, correlation/task IDs, capabilities de proposta/leitura, deadline e hops. Contexto factual chega somente pela Knowledge API com as mesmas restrições da 7D. Mensagem atual é preservada; resultados anteriores são resumidos em tamanho e tratados como UNTRUSTED_DATA. O modelo pode produzir ModelDecision.proposed_actions: o backend valida parâmetros e cria candidato AGENT_PROPOSED em WAITING_AUTHORIZATION. Não cria autorização ou Job. Todas as ferramentas externas permanecem PLANNED/DISABLED.

AgentTask sobrevive à sessão por persistência; WorkflowRun contém papéis, status, uso, contagem, hashes e resultado mínimo. Não contém raciocínio privado. Os papéis podem analisar informações; nenhuma invocação atesta operação em produção.
