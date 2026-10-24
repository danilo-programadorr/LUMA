# Fronteira Control Plane / Local Runtime

7F-A2, 0.6.0rc1, 2026-10-24, verificação Codex.

| Responsabilidade | Autoridade |
| --- | --- |
| Owner, sessão, projeto, grants, Tool Registry | Control Plane |
| Criar task e validade | Control Plane |
| Análise, modelo, Knowledge, agentes | SERVICE_RUNTIME |
| Risk hint / security review | Dado consultivo do runtime |
| Risco efetivo, ActionRequest, estado canônico | Control Plane |
| Aprovação e ExecutionAuthorization | Owner autenticado no Control Plane |
| Lease/job/reconciliação | Control Plane; executor separado |
| Execução externa real | Não habilitada nesta etapa |

RuntimeTaskService resolve Owner pela sessão persistida, nunca por campo recebido
do runtime. Task vincula sessão/projeto/runtime/device, scope, tempo do servidor e
snapshot do registry. Uma task não fornece permissão de execução.
No recebimento de resultado são conferidos: identidade atual, sessão, grants,
acesso Knowledge, projeto, device habilitado/não revogado, correlação, validade,
cancelamento, registry e kill switch. Proposals passam pela política canônica,
normalização de parâmetros e cálculo independente de risco.
Workspace/resource/destination devem coincidir com o escopo aprovado para a task.
Recurso e destino derivados dos parâmetros também devem coincidir.
Ferramentas planejadas/desabilitadas podem gerar proposta segundo a política
existente; isso não cria aprovação, autorização ou job.

Persistência usa agent_tasks existente, com envelope explícito e identificação
do protocolo; não houve alteração de migrations 0001–0004 nem nova tabela.
Deduplicação de task usa a idempotência canônica existente. Resultado usa hash
canônico e resposta persistida na mesma transação da ActionRequest e auditoria.
Upload repetido retorna a mesma resposta; conteúdo divergente é conflito.
PostgreSQL preserva a serialização por schema_version.epoch e READ COMMITTED.
A dupla entrega concorrente foi testada com conexões reais e serviço recriado.

Runtime deduplica por task_id/idempotency_key/fingerprint em cache limitado.
Tarefas diferentes podem processar em paralelo; uma mesma task em andamento
possui evento próprio. Cache até 128 resultados, até 16 tarefas em andamento.
Após restart/eviction pode haver nova análise/custo de modelo: o Control Plane
continua garantindo um único efeito lógico. Não se afirma exactly-once de modelo.

O binding device é fornecido pela integração interna confiável desta etapa.
Não há autenticação remota de device nem endpoint externo de upload.
Assinaturas/enrollment/polling serão tratados no gate próprio. Não expor essas
interfaces internas à rede antes disso. A separação é de imports, contratos e
credenciais da aplicação; não representa sandbox de código Python malicioso.

Workspace é identificador de escopo, não caminho acessível ao runtime remoto.
Ferramentas de escrita filesystem/Codex permanecem indisponíveis; seu futuro
adapter deve validar mapping local e incluir o escopo na autorização executável.
A2 não aprova execução desses adapters.

Testes de processos limpos bloqueiam importação de implementações proibidas.
Control Plane sobe com PATH sem Codex e sem Gemini/Knowledge configurados.
Runtime executa ADK local com provider sintético sem DB canônico nem Owner.
Nenhum teste dessa etapa chama Gemini real ou Codex real.
