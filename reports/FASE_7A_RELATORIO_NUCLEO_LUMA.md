# Fase 7A — Fundação do backend da LUMA

**CONCLUÍDA E VALIDADA LOCALMENTE — LUMA Backend 0.1.0.** Projeto separado em `D:\projetos\luma`, Git local inicializado, sem remote, sem push/deploy e sem commit criado nesta fase. Servidores de teste encerrados. Próxima fase não iniciada.

Data: 2026-10-20. Responsável pela implementação e verificação: Codex, sob [autorização do proprietário](AUTORIZACAO_FASE_7A.txt). Confiança alta para implementação e testes locais indicados. Nenhuma afirmação de operação em produção. Código desta entrega identificado pela versão e pelos hashes em `FASE_7A_HASHES_ENTREGA.json`; não atribuímos um commit inexistente ao backend.

## 1. Estrutura e arquitetura

Estrutura criada: `backend/app`, `backend/tests`, `backend/requirements`, `contracts`, `docs`, `reports`, `.gitignore`, `.env.example`, README e auditoria reproduzível. Módulos coesos (`models`, `config`, `auth`, `registry`, `policy`, `knowledge`, `state`, `audit`, `main`) evitam diretórios vazios e separam responsabilidades. Ambiente Python isolado `.venv`, ignorado pelo Git; dependências fixadas.

LUMA é plataforma WEB RESPONSIVA, com Next.js/TypeScript previstos para frontend futuro. Backend Python/FastAPI nesta fase, sem frontend, Flutter ou APK. LUMA e Cérebro continuam separados. Fluxo implementado: usuário autenticado → principal → projeto → capability/policy → cliente HTTP Knowledge → contexto rastreável. Runtime não importa engine, não lê corpus e não chama subprocessos. Nenhuma lógica de ranking, ACL documental, freshness ou governança do Cérebro foi duplicada.

## 2. Identidade e project registry

Principal explícito: `local-owner`, tipo LOCAL_OWNER, nome genérico, role OWNER, escopo meu-gestor, capability knowledge.read, nível OWNER_SCOPED. A abstração LocalAuthenticator permite substituir a autenticação futuramente. Bearer local e bearer upstream são distintos, vêm de ambiente e não são expostos. OWNER não transfere privilégio a ferramentas/agentes.

Project contém ID, nome, estado, endpoint, modo lexical, enabled, capabilities e metadata. Somente meu-gestor registrado. Registry e KnowledgeService fazem resolução por ID, sem fallback. Cliente ausente ou endpoint divergente é negado. MechAI não implementado; um projeto sintético aparece somente em teste de isolamento.

## 3. Knowledge consumer e KnowledgeContext

KnowledgeClient usa HTTP, timeout configurável, uma repetição no máximo para GET em erro de conexão/timeout e nenhuma repetição de POST. Sem proxies de ambiente, redirects ou endpoint remoto. Base aceita apenas `http://127.0.0.1:<porta>`, sem credenciais/path/query arbitrários. Credencial vem de LUMA_KNOWLEDGE_TOKEN; não é o token que autentica o usuário na LUMA.

Request contém project_id, query, package, include_history e limits; scope, access_level, sensitivity, roles e capabilities enviados pelo cliente são rejeitados. Histórico e packages dependem de configuração explícita e continuam sujeitos à Knowledge API. Query limitada a 2000 caracteres, body 16 KiB, até 5 documentos/12 chunks/16000 caracteres; resposta upstream limitada a 2 MiB.

KnowledgeContext preserva query, project_id, brain_version, engine_version, results, sources, warnings, permission_status, retrieved_at, request_id upstream e correlation_id local. Contexto é marcado UNTRUSTED_DATA. Não contém resposta gerada. IDs/fontes/escopo/orçamento/modo/versões são validados; conteúdo não executa instruções. Estado de autorização é rechecado após HTTP para detectar revogação durante a chamada. Header X-Luma-Correlation-ID é enviado; a Knowledge API atual pode ignorá-lo, e a correlação explícita é preservada na resposta LUMA.

## 4. Capabilities, tools e approval policy

Capability do principal, capability do projeto, associação ao tool e estado enabled são verificações distintas. Somente knowledge/knowledge.read pode passar à admissão nesta fase, mesmo que uma configuração de ferramenta externa fosse alterada. Não existe executor de ferramentas externas.

Tool registry contém Knowledge ENABLED_LOCAL; Google Calendar, Google Tasks, GitHub, Firebase, Codex, Analytics, Google Ads/Meta e PC Runner estão PLANNED/enabled=false. [Registry exportado](../contracts/registries.json). Policy conceitual usa AUTO, CONFIRM e DENY: leituras AUTO; certas criações/edições AUTO quando explicitamente solicitadas pelo OWNER; exclusões, convites/participantes, escrita GitHub, deploy Firebase e execução Codex exigem confirmação. Categoria desconhecida é DENY. Resultado conceitual AUTO não habilita ferramenta.

ActionRequest e ApprovalRecord são contratos separados. A proposta fica vinculada ao conteúdo por hash; alteração arbitrária do requisito ou parâmetros é rejeitada. Aprovação tem action_id, principal, decisão, escopo, prazo de cinco minutos e consumo único; não autoriza outra ação, não ignora revogação e não concede permissão eterna. Os estados de execução futura são vocabulário do contrato, sem máquina executora. Funções administrativas permanecem internas Python, sem endpoints HTTP nesta fase.

## 5. Revogação e kill switch

Policy suporta revogar capability por principal/projeto, desabilitar tool, suspender projeto e estado global RUNNING/PAUSED/LOCKED. PAUSED/LOCKED bloqueiam inclusive leitura Knowledge pela política inicial. Revogação durante HTTP é reavaliada antes de devolver contexto. Nenhuma ação externa pode executar em qualquer estado nesta fase.

Limite explícito: controles são **em memória por processo**. Reinício restaura configuração inicial; não há persistência de kill switch, recovery policy durável ou administração remota. Persistência deve ser projetada antes de introduzir ações mutáveis. Estado conceitual não é apresentado como mecanismo operacional de produção.

## 6. Audit, sessions e learning

Auditoria JSON inclui event_id, timestamp, principal_id, project_id, event_type, tool_id, action_id, result e correlation_id. Cobre chamadas HTTP e operações internas de proposta/aprovação/consumo, revogação/suspensão/estado, criação de sessão e candidato. Não inclui token, query, documentos, intent, parameters ou conteúdo financeiro. Emissão em stdout, sem retenção automática ou garantia de resistência à adulteração.

Session contém dono, projeto ativo validado, datas e status; acesso por outro principal/projeto é negado. Não armazena conversa completa. LearningCandidate contém source, projeto, claim, evidence, confidence, status e data. Registro aceita apenas PROPOSED com evidência; promote() falha com WRITE_BACK_DISABLED. VALIDATED/REJECTED/PROMOTED são contratos futuros, sem fluxo público implementado. Limites locais de 1000 objetos por coleção; reinício descarta estado. Não há escrita canônica.

MEMORY é contexto/preferências/histórico operacional permitido; KNOWLEDGE são fatos canônicos por projeto; LEARNING CANDIDATE não é fato promovido. Fluxo futuro registrado: experiência → candidato → evidência → validação → aprovação quando necessária → write-back. Inferência não se torna verdade automática.

## 7. Agentes, Calendar, Tasks, Gemini e ADK

Nove registros PLANNED: LUMA — Gestora Geral; Produto; Desenvolvimento; Codex / Engenheiro de Código; QA; Segurança; Dados & Analytics; Growth & Marketing; Conteúdo & Social. A autorização cita oito em trechos gerais e nove na lista específica da etapa 25; foi seguida a lista explícita, registrando a divergência. Nenhum agente executável foi criado.

LUMA será a única orquestradora principal. Especialistas não se atribuem privilégios, não chamam tools sem capability, não trocam projeto ativo, não ignoram approvals e não promovem conhecimento sozinhos.

Calendar: contratos para agenda, disponibilidade, criação/edição/exclusão/cancelamento, lembretes e sincronização da conta usada no celular; participantes/convites exigem confirmação. Tasks: leitura/criação/edição/conclusão/reabertura/organização/exclusão, prazos e listas pessoais/de projetos. Nenhuma chamada Google/OAuth.

ModelProvider é somente Protocol Python; provedor futuro Google Gemini API. Framework futuro Google ADK; contratos desacoplados dele. Nenhum SDK Gemini/ADK instalado ou chamado e nenhum motor OpenAI integrado. [Contratos futuros](../docs/CONTRATOS_FUTUROS.md).

## 8. Endpoints e operação local

| Endpoint | Comportamento |
|---|---|
| GET /health | Público, readiness do processo LUMA e versão |
| GET /v1/luma/status | Autenticado, principal/estado e disponibilidade dos projetos |
| GET /v1/projects | Autenticado, registry autorizado e estado Knowledge |
| POST /v1/knowledge/query | Autenticado, política e consumo HTTP, retorna KnowledgeContext |
| GET /v1/tools | Autenticado, ferramentas planejadas/estado efetivo habilitado |
| GET /v1/agents | Autenticado, nove registros futuros |
| GET /openapi.json | Contrato técnico inicial, sem segredo |

Bind do launcher exclusivamente 127.0.0.1:8770, host externo rejeitado. Sem CORS, proxy headers desabilitados, Host restrito a localhost/127.0.0.1. Sem interfaces Swagger/ReDoc externas. Erros não ecoam entrada/stack trace/segredo. LUMA inicia sem Knowledge disponível; /health continua 200, status DEGRADED com projeto UNAVAILABLE e consulta 503.

Start/stop e exemplos no [README](../README.md). Ctrl+C fecha servidor e cliente HTTP. O backend não inicia processos filhos em uso normal. O harness de teste inicia explicitamente o serviço Knowledge aprovado com bytecode externo desabilitado; isso não faz parte do runtime LUMA.

## 9. Testes e segurança

**65/65 testes aprovados, nenhum skip na validação final.** [Saída final](FASE_7A_TESTES_FINAL.txt). Cobertura: identidade, principal, registry/routing, cliente/contexto, capabilities/tools, política, actions/approvals, revogação/kill switch, audit, sessions, learning, agentes e ModelProvider.

Negativos: projeto inexistente e sem cliente, scope/capability ausente, elevação por payload, tools desabilitadas, ação mutável negada inclusive com aprovação, aprovação de outra action/principal/parâmetros/escopo, expirada ou reutilizada, kill switch, prompt injection, token ausente/inválido, API indisponível, response com projeto/modo/permissão/fontes divergentes, orçamento excessivo, query gigante, path extra, malformed JSON e revogação durante I/O.

[Integração real](FASE_7A_INTEGRACAO_KNOWLEDGE.json): oito assuntos — arquitetura, privacidade, riscos, permissão atual, histórico de autorização, revogação/restauração, produto e segurança. Dois servidores reais loopback e engine Node existente. Comparados integralmente results/sources/warnings/permission_status/project_id/status/confidence da LUMA vs Knowledge API direta. Versões preservadas; nenhuma geração natural. A consulta sobre histórico usou política padrão sem habilitar histórico; não é afirmação de acesso a documentos históricos restritos.

Desligamento da Knowledge API deixou LUMA responsiva e degradada, sem inventar contexto. Ao final, ambos servidores e worker Node terminaram. Nenhum serviço ficou rodando. Não se repetiram holdouts nem alterou ranking/corpus. Suítes antigas não foram reexecutadas nesta fase porque seus arquivos foram preservados e integração real exercitou a cadeia existente.

Comandos executados no novo projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements/lock.txt
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:LUMA_TEST_KNOWLEDGE_WORKSPACE='D:\cerebro do gestor'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=runtime/tests-final
.\.venv\Scripts\python.exe audit_workspace.py
```

Execução local Windows/Python3.13.1; FastAPI0.156.2/Pydantic2.14.1/Uvicorn0.54.0/httpx0.28.1. Aviso de depreciação do TestClient Starlette/httpx mantido; não houve falha. Escritas em D:\projetos\luma e sockets locais passaram pela revisão de acesso porque ficam fora das raízes/rede do sandbox atual. Nenhum contorno de aprovação.

## 10. Integridade, arquivos e limitações

[Auditoria](FASE_7A_AUDITORIA.json): 37 hashes da entrega Fase6 e 166 da entrega Fase5F (PLANS antigo excluído, versão Fase6 incluída) preservados, além dos 763 arquivos da fonte investigada. Source main@9fe7fd3a69a537f9e67953b7028e64c676a48547 e Git limpo. Corpus0.6.0, engine1.4.0 e Knowledge API0.1.0 intactos. Repositório `D:\projetos\meu_gestor_financeiro` consultado apenas via Git read-only, mesmo HEAD e árvore limpa; não se alega comparação com um baseline financeiro anterior inexistente nesta fase.

Scan de padrões de segredos e inspeção de imports/runtime sem achados; tokens reais não foram persistidos. Scanner é heurístico e não substitui revisão especializada. Manifesto de arquivos com hashes identifica código, contratos, documentação, testes e relatórios; `.venv`, `.git`, caches e `runtime` excluídos. Nenhuma alteração necessária no Cérebro, app financeiro ou produção. Git LUMA sem remoto, sem push e sem commit; mudanças são arquivos locais novos.

Limitações: um único owner/token por instância, estado efêmero em memória, logs não duráveis, sem OAuth/TLS/multiusuário, timeout por operação HTTP (não deadline global), integração avaliada em ambiente local e conjunto pequeno, sem SLA. Approval/learning/sessions são serviços internos e contratos, não funcionalidades finais de produto. Não há executor, persistência operacional, frontend, modelo/IA, Google, agentes ou deploy. Dados retornados são conteúdo não confiável para qualquer consumidor futuro.

## 11. Versão, recomendação e parada

**LUMA Backend 0.1.0** validado localmente. Próxima fase recomendada, somente após autorização: definir persistência dos controles/identidades e a superfície administrativa antes de conectar agentes ou ações mutáveis. As regras de consentimento e confirmação deverão vir de interação humana autenticada, jamais de uma variável enviada por LLM.

**Fase 7A encerrada.** Não conectar Gemini, instalar ADK, conectar Calendar/Tasks, criar frontend/agentes, fazer deploy ou push. Aguardar autorização explícita.
