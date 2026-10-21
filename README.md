# LUMA Backend 0.2.0 â€” control plane local durÃ¡vel

Plataforma web responsiva futura, backend Python/FastAPI local. SQLite + SQLAlchemy persistem identidade, controles, aÃ§Ãµes/aprovaÃ§Ãµes, sessÃµes, candidatos e auditoria. **Somente Knowledge HTTP executa; nenhum modelo, agente ou ferramenta externa foi integrado.** CÃ©rebro Meu Gestor permanece separado e intacto.

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

Bind somente `127.0.0.1:8770`. Ctrl+C encerra o backend e fecha HTTP/DB. LUMA nÃ£o inicia a Knowledge API em uso normal. Sem Knowledge disponÃ­vel, LUMA inicia, `/health` responde e status indica DEGRADED; consultas nÃ£o inventam contexto. Sem migraÃ§Ã£o, startup falha fechado. Banco padrÃ£o: `runtime/luma.db`, ignorado pelo Git. NÃ£o hÃ¡ reset automÃ¡tico.

Os trÃªs segredos sÃ£o distintos, somente por ambiente e nÃ£o sÃ£o persistidos. `.env.example` tem valores vazios; `.env` nÃ£o Ã© carregado automaticamente. NÃ£o imprimir/copiar segredos para relatÃ³rios ou histÃ³rico. Credencial administrativa adicional deve ficar sob controle humano e nunca ser disponibilizada a LLM/agente futuro. NÃ£o Ã© OAuth/MFA, nem prova tÃ©cnica de quem estÃ¡ diante do terminal.

Default de timeout HTTP: trÃªs segundos por operaÃ§Ã£o, GET com atÃ© uma repetiÃ§Ã£o em falha de conexÃ£o/timeout; POST sem retry. Host externo, database URL fora de runtime, endpoint remoto, redirects e proxies de ambiente sÃ£o rejeitados/desabilitados. `LUMA_KNOWLEDGE_HISTORY=false` e `LUMA_KNOWLEDGE_PACKAGES` vazio formam configuraÃ§Ã£o **inicial** persistida no bootstrap. ReinÃ­cio nÃ£o sobrescreve opÃ§Ãµes, permissÃµes ou controles existentes.

## Consultar

```powershell
$base='http://127.0.0.1:8770'
$headers=@{Authorization="Bearer $env:LUMA_OWNER_TOKEN"}
Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/v1/luma/status" -Headers $headers
Invoke-RestMethod "$base/v1/admin/state" -Headers $headers
Invoke-RestMethod "$base/v1/admin/tools" -Headers $headers
$body=@{project_id='meu-gestor';query='Como funciona a arquitetura tÃ©cnica?'} | ConvertTo-Json
Invoke-RestMethod "$base/v1/knowledge/query" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Health/OpenAPI pÃºblicos, `/v1/*` autenticado. CORS nÃ£o habilitado. Sources/warnings/permission_status preservados; KnowledgeContext Ã© dado nÃ£o confiÃ¡vel, nÃ£o instruÃ§Ã£o nem resposta gerada. Seu conteÃºdo nÃ£o Ã© salvo no audit/DB. Estado PAUSED/LOCKED bloqueia Knowledge; admin permanece disponÃ­vel apenas pelas capabilities especÃ­ficas, para recuperaÃ§Ã£o autorizada.

## MudanÃ§as administrativas

Cada mutaÃ§Ã£o exige `Idempotency-Key` de 8â€“128 caracteres alfanumÃ©ricos, `_` ou `-`. Mesma chave + mesmo principal/operaÃ§Ã£o/payload retorna a resposta original sem repetir a mudanÃ§a. Mesma chave com outro pedido: 409. Resposta repetida Ã© snapshot original: consultar GET para estado atual.

```powershell
$mutation=@{Authorization="Bearer $env:LUMA_OWNER_TOKEN"; 'Idempotency-Key'=[guid]::NewGuid().ToString('N')}
Invoke-RestMethod "$base/v1/admin/state" -Method Post -Headers $mutation -ContentType 'application/json' -Body '{"state":"LOCKED"}'
# Desbloqueio exige capability admin.state.unlock + confirmaÃ§Ã£o explÃ­cita + segredo adicional.
$unlock=@{Authorization="Bearer $env:LUMA_OWNER_TOKEN"; 'Idempotency-Key'=[guid]::NewGuid().ToString('N'); 'X-Admin-Confirmation'=$env:LUMA_ADMIN_CONFIRM_TOKEN}
Invoke-RestMethod "$base/v1/admin/state" -Method Post -Headers $unlock -ContentType 'application/json' -Body '{"state":"RUNNING","confirmation":"UNLOCK_LUMA"}'
```

Aprovar/recusar usa `/v1/admin/approvals/{action_id}/decision`, decision APPROVE/DENY, scope obtido da aÃ§Ã£o, confirmation HUMAN_DECISION e header de confirmaÃ§Ã£o adicional. `approved=true` nÃ£o existe no contrato. Consumo de aprovaÃ§Ã£o Ã© **validaÃ§Ã£o administrativa sem execuÃ§Ã£o**: grava consumed_at e cancela a aÃ§Ã£o atomicamente. Nunca chama ferramenta. AprovaÃ§Ãµes expiram em cinco minutos, sÃ£o especÃ­ficas e nÃ£o reutilizÃ¡veis. Estado/capabilities atuais sÃ£o verificados antes de novos efeitos.

[Control plane, rotas e polÃ­ticas](docs/CONTROL_PLANE_7B.md) Â· [Arquitetura](docs/ARQUITETURA.md) Â· [OpenAPI](contracts/openapi.json)

## Backup e reset local

Backup consistente pelo mecanismo SQLite, sem sincronizaÃ§Ã£o externa:

```powershell
.\.venv\Scripts\python.exe -m backend.maintenance backup
```

Cria snapshot em `runtime/backups/`, verifica integridade e nÃ£o modifica a origem. Ã‰ possÃ­vel com serviÃ§o ativo pelo mecanismo transacional SQLite; para copiar arquivo manualmente, parar primeiro o serviÃ§o. Backups podem conter metadados privados: manter locais, com acesso de SO limitado, fora do Git.

**Reset de desenvolvimento Ã© manual e explÃ­cito**, nunca startup. Pare todas as instÃ¢ncias LUMA, faÃ§a backup e sÃ³ entÃ£o, se quiser realmente recomeÃ§ar, execute:

```powershell
if ((Read-Host 'Digite RESET_LOCAL_LUMA para arquivar o banco e recomeÃ§ar') -cne 'RESET_LOCAL_LUMA') { throw 'Reset cancelado' }
$root=(Resolve-Path 'D:\projetos\luma\runtime').Path
$db=(Resolve-Path -LiteralPath (Join-Path $root 'luma.db')).Path
if ([IO.Path]::GetDirectoryName($db) -ne $root) { throw 'Caminho invÃ¡lido' }
$archive=Join-Path $root ('luma-before-reset-'+[guid]::NewGuid().ToString('N')+'.db')
Move-Item -LiteralPath $db -Destination $archive
.\.venv\Scripts\python.exe -m backend.migrate upgrade
```

Procedimento acima vale para o banco padrÃ£o, com aplicaÃ§Ã£o parada e sem journal ativo; nÃ£o executar com transaÃ§Ã£o aberta. Guarda o original, sem apagar. Para restaurar, pare a aplicaÃ§Ã£o e restaure um backup verificado para a localizaÃ§Ã£o configurada; nÃ£o mescle arquivos de bancos diferentes. Nenhum reset foi executado durante a entrega.

## Testes e auditoria

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:LUMA_TEST_KNOWLEDGE_WORKSPACE='D:\cerebro do gestor'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=runtime/test-local
.\.venv\Scripts\python.exe audit_workspace.py
```

Use pasta basetemp exclusiva: pytest a limpa. Sem variÃ¡vel de Knowledge, a integraÃ§Ã£o real Ã© marcada skip; na entrega ela foi executada. Bancos de teste sÃ£o isolados em runtime; nÃ£o usam o banco operacional. Testes locais de sockets e escrita fora do sandbox exigiram revisÃ£o autorizada do ambiente.

[RelatÃ³rio 7B](reports/FASE_7B_RELATORIO_PERSISTENCIA_CONTROL_PLANE.md). Contratos Calendar/Tasks/Gemini/ADK e nove agentes continuam futuros. Sem frontend, deploy, remote ou push. Parar nesta fase.


## Owner e runtime na versão 0.3.0

[Política vigente de confiança](docs/TRUST_BOUNDARY_7C.md) · [LUMA Web: voz e núcleo visual](docs/LUMA_WEB_REQUISITOS.md).

Faça backup antes do upgrade explícito 0001→0002. A migração preserva dados existentes e acrescenta grants, retenção e cadeia auditável. v0001 permanece intacta. LUMA_TOKEN é alias legado do owner; não configure aliases com valores diferentes. Runtime sem LUMA_RUNTIME_TOKEN fica inacessível, sem fallback para owner.

Owner usa rotas humanas; runtime usa exclusivamente /v1/runtime e recebe 403 em admin. O humano cria uma sessão por POST /v1/admin/sessions; somente o session_id resultante deve ser passado ao runtime. POST /v1/runtime/knowledge/query exige esse session_id junto de project_id/query. Rotas de proposta recebem apenas sessão, intenção e dados; origem/risco/permissão são derivados pelo backend. Não há execução externa. Revogar grants, fechar sessão, desabilitar projeto/tool ou LOCKED bloqueia uso atual.

GET /v1/admin/grants lista autoridade durável. POST /v1/admin/grants e /grants/{id}/revoke exigem grants administrativos humanos; autoatribuição é proibida. GET /v1/admin/audit/verify verifica cadeia; /retention/preview não apaga nada. Retenção NO_AUTO_DELETE nas cinco categorias. O runtime não tem acesso ao audit administrativo.
