# LUMA Backend 0.2.0 — control plane local durável

Plataforma web responsiva futura, backend Python/FastAPI local. SQLite + SQLAlchemy persistem identidade, controles, ações/aprovações, sessões, candidatos e auditoria. **Somente Knowledge HTTP executa; nenhum modelo, agente ou ferramenta externa foi integrado.** Cérebro Meu Gestor permanece separado e intacto.

## Instalar, migrar e iniciar no Windows

Na pasta `D:\projetos\luma`, Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements/lock.txt
$env:LUMA_DATABASE_URL='sqlite:///runtime/luma.db'
.\.venv\Scripts\python.exe -m backend.migrate upgrade
$env:LUMA_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
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
$headers=@{Authorization="Bearer $env:LUMA_TOKEN"}
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
$mutation=@{Authorization="Bearer $env:LUMA_TOKEN"; 'Idempotency-Key'=[guid]::NewGuid().ToString('N')}
Invoke-RestMethod "$base/v1/admin/state" -Method Post -Headers $mutation -ContentType 'application/json' -Body '{"state":"LOCKED"}'
# Desbloqueio exige capability admin.state.unlock + confirmação explícita + segredo adicional.
$unlock=@{Authorization="Bearer $env:LUMA_TOKEN"; 'Idempotency-Key'=[guid]::NewGuid().ToString('N'); 'X-Admin-Confirmation'=$env:LUMA_ADMIN_CONFIRM_TOKEN}
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

[Relatório 7B](reports/FASE_7B_RELATORIO_PERSISTENCIA_CONTROL_PLANE.md). Contratos Calendar/Tasks/Gemini/ADK e nove agentes continuam futuros. Sem frontend, deploy, remote ou push. Parar nesta fase.
