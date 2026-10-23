# LUMA Backend 0.5.0rc1 — Fase 7E candidata

Plataforma web responsiva futura, backend Python/FastAPI local. SQLite + SQLAlchemy persistem identidade, controles, ações/aprovações, sessões, candidatos e auditoria. **Knowledge HTTP funciona; o adaptador Gemini foi validado localmente e em oito cenários reais com gemini-3.8-flash. A candidata 7E integra nove papéis via ADK e execução durável local; a validação real ADK + Gemini ainda está pendente. Ferramentas externas mutáveis permanecem desabilitadas.** Cérebro Meu Gestor permanece separado e intacto.

## Instalar, migrar e iniciar no Windows

Na pasta `D:\projetos\luma`, Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements/lock.txt
$env:LUMA_DATABASE_URL='sqlite:///runtime/luma.db'
.\.venv\Scripts\python.exe -m backend.migrate upgrade
$env:LUMA_OWNER_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$env:LUMA_RUNTIME_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$env:LUMA_ADMIN_CONFIRM_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$secure=Read-Host 'Token configurado na Knowledge API local' -AsSecureString
$env:LUMA_KNOWLEDGE_TOKEN=[Net.NetworkCredential]::new('', $secure).Password
$env:LUMA_KNOWLEDGE_ENDPOINT='http://127.0.0.1:8765'
.\.venv\Scripts\python.exe -m backend
```

Bind somente `127.0.0.1:8770`. Ctrl+C encerra o backend e fecha HTTP/DB. LUMA não inicia a Knowledge API em uso normal. Sem Knowledge disponível, LUMA inicia, `/health` responde e status indica DEGRADED; consultas não inventam contexto. Sem migração, startup falha fechado. Banco padrão: `runtime/luma.db`, ignorado pelo Git. Não há reset automático.

Os três segredos são distintos, somente por ambiente e não são persistidos. `.env.example` tem valores vazios; `.env` não é carregado automaticamente. Não imprimir/copiar segredos para relatórios ou histórico. Credencial administrativa adicional deve ficar sob controle humano e nunca ser disponibilizada a LLM/agente futuro. Não é OAuth/MFA, nem prova técnica de quem está diante do terminal.

Default de timeout HTTP: três segundos por operação, GET com até uma repetição em falha de conexão/timeout; POST sem retry. Host externo, database URL fora de runtime, endpoint remoto, redirects e proxies de ambiente são rejeitados/desabilitados. `LUMA_KNOWLEDGE_HISTORY=false` e `LUMA_KNOWLEDGE_PACKAGES` vazio formam configuração **inicial** persistida no bootstrap. Reinício não sobrescreve opções, permissões ou controles existentes.

## Consultar

```powershell
$base='http://127.0.0.1:8770'
$headers=@{Authorization="Bearer $env:LUMA_OWNER_TOKEN"}
Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/v1/luma/status" -Headers $headers
Invoke-RestMethod "$base/v1/admin/state" -Headers $headers
Invoke-RestMethod "$base/v1/admin/tools" -Headers $headers
$body=@{project_id='meu-gestor';query='Como funciona a arquitetura técnica?'} | ConvertTo-Json
Invoke-RestMethod "$base/v1/knowledge/query" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Health/OpenAPI públicos, `/v1/*` autenticado. CORS não habilitado. Sources/warnings/permission_status preservados; KnowledgeContext é dado não confiável, não instrução nem resposta gerada. Seu conteúdo não é salvo no audit/DB. Estado PAUSED/LOCKED bloqueia Knowledge; admin permanece disponível apenas pelas capabilities específicas, para recuperação autorizada.

## Mudanças administrativas

Cada mutação exige `Idempotency-Key` de 8–128 caracteres alfanuméricos, `_` ou `-`. Mesma chave + mesmo principal/operação/payload retorna a resposta original sem repetir a mudança. Mesma chave com outro pedido: 409. Resposta repetida é snapshot original: consultar GET para estado atual.

```powershell
$mutation=@{Authorization="Bearer $env:LUMA_OWNER_TOKEN"; 'Idempotency-Key'=[guid]::NewGuid().ToString('N')}
Invoke-RestMethod "$base/v1/admin/state" -Method Post -Headers $mutation -ContentType 'application/json' -Body '{"state":"LOCKED"}'
# Desbloqueio exige capability admin.state.unlock + confirmação explícita + segredo adicional.
$unlock=@{Authorization="Bearer $env:LUMA_OWNER_TOKEN"; 'Idempotency-Key'=[guid]::NewGuid().ToString('N'); 'X-Admin-Confirmation'=$env:LUMA_ADMIN_CONFIRM_TOKEN}
Invoke-RestMethod "$base/v1/admin/state" -Method Post -Headers $unlock -ContentType 'application/json' -Body '{"state":"RUNNING","confirmation":"UNLOCK_LUMA"}'
```

Aprovar/recusar usa `/v1/admin/approvals/{action_id}/decision`, decision APPROVE/DENY, scope obtido da ação, confirmation HUMAN_DECISION e header de confirmação adicional. `approved=true` não existe no contrato. Consumo de aprovação é **validação administrativa sem execução**: grava consumed_at e cancela a ação atomicamente. Nunca chama ferramenta. Aprovações expiram em cinco minutos, são específicas e não reutilizáveis. Estado/capabilities atuais são verificados antes de novos efeitos.

[Control plane, rotas e políticas](docs/CONTROL_PLANE_7B.md) · [Arquitetura](docs/ARQUITETURA.md) · [OpenAPI](contracts/openapi.json)

## Backup e reset local

Backup consistente pelo mecanismo SQLite, sem sincronização externa:

```powershell
.\.venv\Scripts\python.exe -m backend.maintenance backup
```

Cria snapshot em `runtime/backups/`, verifica integridade e não modifica a origem. É possível com serviço ativo pelo mecanismo transacional SQLite; para copiar arquivo manualmente, parar primeiro o serviço. Backups podem conter metadados privados: manter locais, com acesso de SO limitado, fora do Git.

**Reset de desenvolvimento é manual e explícito**, nunca startup. Pare todas as instâncias LUMA, faça backup e só então, se quiser realmente recomeçar, execute:

```powershell
if ((Read-Host 'Digite RESET_LOCAL_LUMA para arquivar o banco e recomeçar') -cne 'RESET_LOCAL_LUMA') { throw 'Reset cancelado' }
$root=(Resolve-Path 'D:\projetos\luma\runtime').Path
$db=(Resolve-Path -LiteralPath (Join-Path $root 'luma.db')).Path
if ([IO.Path]::GetDirectoryName($db) -ne $root) { throw 'Caminho inválido' }
$archive=Join-Path $root ('luma-before-reset-'+[guid]::NewGuid().ToString('N')+'.db')
Move-Item -LiteralPath $db -Destination $archive
.\.venv\Scripts\python.exe -m backend.migrate upgrade
```

Procedimento acima vale para o banco padrão, com aplicação parada e sem journal ativo; não executar com transação aberta. Guarda o original, sem apagar. Para restaurar, pare a aplicação e restaure um backup verificado para a localização configurada; não mescle arquivos de bancos diferentes. Nenhum reset foi executado durante a entrega.

## Testes e auditoria

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:LUMA_TEST_KNOWLEDGE_WORKSPACE='D:\cerebro do gestor'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=runtime/test-local
.\.venv\Scripts\python.exe audit_workspace.py
```

Use pasta basetemp exclusiva: pytest a limpa. Sem variável de Knowledge, a integração real é marcada skip; na entrega ela foi executada. Bancos de teste são isolados em runtime; não usam o banco operacional. Testes locais de sockets e escrita fora do sandbox exigiram revisão autorizada do ambiente.

[Relatório 7B](reports/FASE_7B_RELATORIO_PERSISTENCIA_CONTROL_PLANE.md). Contratos Calendar/Tasks/ADK e nove agentes continuam futuros; Gemini é adaptador candidato ainda sem validação real. Sem frontend, deploy, remote ou push. Parar nesta fase.


## Owner e runtime na versão 0.3.0

[Política vigente de confiança](docs/TRUST_BOUNDARY_7C.md) · [LUMA Web: voz e núcleo visual](docs/LUMA_WEB_REQUISITOS.md).

Faça backup antes do upgrade explícito 0001→0002. A migração preserva dados existentes e acrescenta grants, retenção e cadeia auditável. v0001 permanece intacta. LUMA_TOKEN é alias legado do owner; não configure aliases com valores diferentes. Runtime sem LUMA_RUNTIME_TOKEN fica inacessível, sem fallback para owner.

Owner usa rotas humanas; runtime usa exclusivamente /v1/runtime e recebe 403 em admin. O humano cria uma sessão por POST /v1/admin/sessions; somente o session_id resultante deve ser passado ao runtime. POST /v1/runtime/knowledge/query exige esse session_id junto de project_id/query. Rotas de proposta recebem apenas sessão, intenção e dados; origem/risco/permissão são derivados pelo backend. Não há execução externa. Revogar grants, fechar sessão, desabilitar projeto/tool ou LOCKED bloqueia uso atual.

GET /v1/admin/grants lista autoridade durável. POST /v1/admin/grants e /grants/{id}/revoke exigem grants administrativos humanos; autoatribuição é proibida. GET /v1/admin/audit/verify verifica cadeia; /retention/preview não apaga nada. Retenção NO_AUTO_DELETE nas cinco categorias. O runtime não tem acesso ao audit administrativo.


## Fase 7D — histórico da conversa e modelo aprovado

[Arquitetura do model layer](docs/MODEL_LAYER_7D.md) · [Relatório 7D](reports/FASE_7D_RELATORIO_GEMINI_MODEL_ADAPTER.md).

A versão 0.4.0 da Fase 7D exigia schema 0003; a candidata atual exige 0004. Faça backup antes de executar a migração explícita. Não altera as migrações 0001/0002. Há janela conversacional limitada e metadados de turnos, separados do audit. Tokens e chave Gemini não são persistidos. Sem chave, admin e Knowledge continuam operacionais; geração retorna MODEL_UNAVAILABLE.

Endpoint humano: POST /v1/conversation/turn, Authorization do owner e Idempotency-Key único. Corpo: session_id de uma sessão criada pelo humano, user_message e locale opcional. O cliente não recebe runtime token e não escolhe temperatura, tools ou teto. Resposta traz mensagem, fontes validadas, warnings, confiança de recuperação/modelo, freshness, status, uso e propostas sem execução. Se Knowledge faltar, a conversa falha fechada.

Para validar Gemini real, configure em um terminal local. Não cole a chave no chat:

```powershell
$env:LUMA_MODEL_PROVIDER='gemini'
# Modelo validado em oito cenários reais da Fase 7D.
$env:LUMA_GEMINI_MODEL='gemini-3.8-flash'
$geminiSecret=Read-Host 'Chave Gemini' -AsSecureString
$env:LUMA_GEMINI_API_KEY=[Net.NetworkCredential]::new('', $geminiSecret).Password
.\.venv\Scripts\python.exe -m backend.validate_gemini
```

O validador executa no máximo sete gerações e um cenário de Knowledge indisponível, usando banco temporário e tokens locais efêmeros. Grava somente resultados/métricas em reports/FASE_7D_GEMINI_REAL.json. Sem chave, retorna BLOCKED_NEEDS_CREDENTIAL sem rede. Reexecutá-lo atualiza esse relatório; aprovação da fase exige inspeção do resultado real e novo fechamento. API/modelo e disponibilidade na conta não são presumidos a partir do nome. Uma chave configurada em outro terminal não é automaticamente herdada por este processo.

A Fase 7D foi aprovada em 0.4.0 e a 7E recebeu autorização específica. A candidata 7E exige evidências próprias e não autoriza iniciar a 7F. O comando acima pertence à validação histórica 7D; para a rodada atual use backend.validate_adk abaixo.


## Fase 7E — operação local e validação

Candidata com ADK isolado, tarefas persistentes, autorizações e jobs. Fase 7D permanece aprovada no histórico; 7E exige validação própria. Nenhuma ferramenta externa mutável é habilitada. Veja docs/LUMA_ADK_ARCHITECTURE.md, docs/LUMA_LOCAL_EXECUTOR.md e docs/LUMA_JOB_RUNTIME.md.

Instale o ambiente ADK separado sem alterar o lock da API:

```powershell
.\.venv\Scripts\python.exe -m venv runtime/adk-venv
.\runtime\adk-venv\Scripts\python.exe -m pip install -r backend/requirements/adk-lock.txt
.\runtime\adk-venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m backend.migrate upgrade
```

Backup antes de migrar DB existente, conforme seção acima. Schema agora 0004; nenhuma migration antiga foi editada. API: python -m backend. Em processos separados com ambiente mínimo (sem OWNER/ADMIN/RUNTIME/Knowledge/Gemini tokens):

```powershell
.\.venv\Scripts\python.exe -m backend.scheduler --once
.\.venv\Scripts\python.exe -m backend.executor_worker --once
.\.venv\Scripts\python.exe -m backend.local_executor --once
```

Sem --once, loops locais. Scheduler/executor usam LUMA_DATABASE_URL local; local_executor usa LUMA_CONTROL_PLANE_URL, LUMA_DEVICE_ID e credencial de device obtida por enrollment humano, sem chave literal em comando. .env.example contém somente nomes/valores vazios e não é carregado automaticamente. Não iniciar executor no shell que contém credenciais privilegiadas. Clientes não habilitam TestTool; teste sandbox exclusivamente nos harnesses.

Testes dirigidos (PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; basetemp deve ficar em runtime):

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_orchestration.py -q --basetemp=runtime/test-adk
.\.venv\Scripts\python.exe -m pytest backend/tests/test_execution_processes.py -q --basetemp=runtime/test-offline-restart
.\.venv\Scripts\python.exe -m backend.validate_adk --case legitimate_proposal
# Somente depois de PASSED no isolado da mesma candidata:
.\.venv\Scripts\python.exe -m backend.validate_adk
```

O último comando usa a sessão segura Gemini já existente e para na primeira falha; não executa ferramentas externas. Testes owner-offline/restart usam processos reais, identidades sintéticas e TestTool local. Resultados em reports/FASE_7E_*. APIs novas: /v1/tasks, /v1/workflows, /v1/action-requests, /v1/execution-authorizations, /v1/jobs, /v1/execution-devices e heartbeat/poll restritos /v1/device. Contratos em contracts/openapi.json. Plano híbrido 7F documentado, sem deploy/autorização para iniciá-lo.

A correção dirigida 7E preserva a rodada real anterior 9/10. O diagnóstico isolado gera reports/FASE_7E_ADK_LEGITIMATE_PROPOSAL_REAL.json; a suíte completa exige PASSED nesse arquivo com o mesmo hash dos fontes executáveis. Falha de schema registra apenas campos/tipos permitidos, sem conteúdo do modelo. Envie somente o relatório JSON sanitizado.
