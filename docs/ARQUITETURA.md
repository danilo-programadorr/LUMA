# Arquitetura da fundação LUMA

Status: IMPLEMENTADO E TESTADO LOCALMENTE quando descrito como runtime; contratos futuros explicitamente separados abaixo. Versão 0.1.0, data 2026-10-20, verificador Codex; confiança alta para código/testes locais. Evidências e limites em `../reports/FASE_7A_RELATORIO_NUCLEO_LUMA.md`. Nenhuma operação de produção foi verificada.

## Fronteiras

Usuário → autenticação local → principal OWNER → project registry → policy/capability → KnowledgeClient HTTP → Knowledge API → contexto rastreável. Após I/O, escopo/revogação são reavaliados antes da liberação do contexto. LUMA é consumidora/orquestradora futura; Cérebro é fonte canônica independente. Nenhuma leitura de corpus, execução Node ou duplicação da engine existe em `backend/app`.

Módulos compactos em `backend/app`, em vez de diretórios vazios para cada conceito: `models` (contratos), `auth`, `config`, `registry`, `policy`, `state`, `knowledge`, `audit` e `main`. Essa divisão permite trocar autenticação, storage e provedor sem dependência de Google ADK. Python/FastAPI/Pydantic/httpx/Uvicorn; dependências fixadas incluem ferramentas de teste. Ambiente virtual próprio da LUMA.

## Identidade e autorização

LocalAuthenticator resolve bearer para Principal configurado pelo servidor. OWNER é papel do usuário, não privilégio automático de agentes/ferramentas. Principal inicial: local-owner, LOCAL_OWNER, display genérico, escopo meu-gestor, capability knowledge.read, approval_level OWNER_SCOPED. Token de entrada e token upstream são distintos, exclusivamente por ambiente no launcher. Sem OAuth/Google Login nesta fase.

Project registry contém somente meu-gestor, ACTIVE/enabled, endpoint local fixado pela configuração, lexical e metadados de versão. Há seleção explícita do cliente por ID e validação do endpoint. Projeto desconhecido ou cliente ausente falha fechado, sem fallback para Meu Gestor. MechAI não está registrado nem implementado.

Policy exige simultaneamente scope, capability do usuário, capability do projeto, ferramenta habilitada e ausência de revogação/suspensão. Mesmo uma configuração de ferramenta externa habilitada acidentalmente não passa a admissão desta fase: somente tool knowledge/capability knowledge.read é admitida. Retornar autorização de admissão não executa uma ferramenta; não há executor externo.

## Consumo e confiança

Health/status GET têm no máximo uma repetição em erro de conexão/timeout, com espera de 20 ms; POST query não é repetido. Timeout configurável 0,05–10 segundos **por operação de transporte**, não deadline total da rota; query inclui status e POST, e status pode repetir. HTTP sem redirects, sem proxies de ambiente; endpoint restrito a http://127.0.0.1 com porta explícita, sem credenciais, query ou path arbitrário. Resposta limitada a 2 MiB. Body de entrada 16 KiB, query até 2000 caracteres, limites de contexto iguais à Knowledge API.

Valida projeto/modo/versões de status (Knowledge API health 0.1.0, corpus 0.6.0, engine 1.4.0), permission_status, orçamento e correspondência de resultados/fontes. Essa checagem é contrato de transporte, não reimplementação de ranking/ACL. Preserva integralmente dicionários results/sources e warnings. Conteúdo da query e excerpt pode conter instruções adversariais: fica inerte, não muda policy nem chama ferramentas. request_id upstream é preservado; correlation_id local é gerado pelo servidor e enviado no header X-Luma-Correlation-ID. A Knowledge API atual pode ignorar esse header; o vínculo explícito está no KnowledgeContext devolvido.

KnowledgeContext guarda query, versões, contextos, proveniência, warnings, permission_status, retrieved_at e IDs; não é persistido indiscriminadamente. A API não devolve answer/resposta gerada e não possui provedor real de modelos.

## Estado e governança

RUNNING/PAUSED/LOCKED são estado local de processo. Nesta política, PAUSED e LOCKED bloqueiam inclusive knowledge.read. Existem revogar capability, desabilitar tool e suspender projeto. Mudanças são API interna Python, sem endpoint HTTP administrativo aberto nesta fase. Reiniciar processo descarta alterações e restaura configuração inicial; não há controle durável de emergência. Isso deve ser resolvido antes de ferramentas mutáveis, que permanecem impossibilitadas agora.

Propostas de ação são vinculadas ao conteúdo por hash no registro interno; approval_requirement não é livremente aceito de caller futuro. ApprovalRecord vincula action_id, principal, hash/escopo, decisão e prazo de cinco minutos; consumo único, rejeita action diferente, alteração de parâmetros, expiração, principal diferente, revogação e estado bloqueado. Aprovação não concede capability nem habilita ferramenta. Campos EXECUTING/SUCCEEDED/FAILED/CANCELLED existem como contrato; não há máquina executora de ações nesta fase.

LocalState mantém até 1000 sessões e 1000 candidatos de aprendizado em memória; Policy limita a 1000 propostas e 1000 approvals, devolvendo erro ao atingir capacidade. Sessões possuem dono, projeto ativo validado, datas e status; não armazenam conversa completa. Dados são efêmeros, reinício os descarta. APIs Python internas não são superfície de autorização pública; futura camada HTTP administrativa precisará autenticar e derivar evidência de pedido humano, nunca aceitar explicit_owner de LLM.

## Auditoria e lifecycle

Eventos JSON em stdout: event_id, timestamp, principal_id, project_id, event_type, tool_id, action_id, result e correlation_id. HTTP, propostas/aprovações, consumo, revogação, suspensão, estado global e criação de sessão/candidato emitem metadados. Nunca intent, parâmetros, query, excerpt, token ou conteúdo financeiro. Sem retenção/arquivo automático, sem prova de durabilidade ou resistência a adulteração. Logs de acesso Uvicorn e diagnósticos informativos httpx desabilitados no launcher. Um coletor seguro é trabalho futuro.

LUMA inicia sem chamar Knowledge API no startup; indisponibilidade é exibida como DEGRADED/UNAVAILABLE em consultas de status. Lifespan fecha conexões HTTP; LUMA não possui processos filhos em operação normal. Testes iniciam/encerram ambos servidores e verificam término do worker Node da Knowledge API. Bind apenas loopback, sem CORS e sem confiança em forwarded headers. Health/OpenAPI não expõem segredos. Sem TLS, autenticação federada, multiusuário, frontend, serviço Windows ou SLA de produção.
