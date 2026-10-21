# LUMA Backend 0.1.0

Fundação local da LUMA, plataforma **web responsiva**. Frontend futuro: Next.js + TypeScript; nenhum frontend/Flutter/APK nesta entrega. Backend Python/FastAPI, sem geração de IA. Cérebro Meu Gestor permanece um projeto independente, consumido exclusivamente por HTTP pelo código da aplicação.

## Instalar e executar no Windows

Na pasta `D:\projetos\luma`, com Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements/lock.txt
$env:LUMA_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
# Forneça de modo privado o token configurado no servidor Knowledge API.
# Não cole o segredo no histórico de comandos nem grave em documentação.
$secure = Read-Host 'Token da Knowledge API local' -AsSecureString
$env:LUMA_KNOWLEDGE_TOKEN = [Net.NetworkCredential]::new('', $secure).Password
$env:LUMA_KNOWLEDGE_ENDPOINT = 'http://127.0.0.1:8765'
.\.venv\Scripts\python.exe -m backend
```

Escuta somente `127.0.0.1:8770`; **Ctrl+C** encerra o servidor e fecha o cliente HTTP. Não inicia ou administra a Knowledge API em produção/local normal. Se ela estiver desligada, a LUMA inicia, health retorna ok, status retorna DEGRADED e consultas falham com 503 sem fabricar contexto. Para uso real local, iniciar a Knowledge API pelo README próprio com o token correspondente. Os tokens LUMA e Knowledge devem ser distintos e aleatórios (32–256 caracteres). `.env.example` não contém segredo; `.env` é ignorado e não é carregado automaticamente.

Variáveis adicionais: `LUMA_HOST` (somente 127.0.0.1), `LUMA_PORT` (8770), `LUMA_TIMEOUT` (3 segundos por operação de transporte), `LUMA_KNOWLEDGE_HISTORY` (false), `LUMA_KNOWLEDGE_PACKAGES` (allowlist vazia). Habilitar histórico/package local não supera as permissões do principal autenticado na Knowledge API. Não há modo semantic/hybrid na LUMA.

## Uso local

Em uma sessão com o token LUMA disponível no ambiente:

```powershell
$base='http://127.0.0.1:8770'
$headers=@{Authorization="Bearer $env:LUMA_TOKEN"}
Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/v1/luma/status" -Headers $headers
Invoke-RestMethod "$base/v1/projects" -Headers $headers
Invoke-RestMethod "$base/v1/tools" -Headers $headers
Invoke-RestMethod "$base/v1/agents" -Headers $headers
$body=@{project_id='meu-gestor';query='Como funciona a arquitetura técnica?'} | ConvertTo-Json
Invoke-RestMethod "$base/v1/knowledge/query" -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Health e OpenAPI são públicos; todas as rotas `/v1/` autenticam o principal local. CORS não habilitado; proxy headers ignorados. A resposta KnowledgeContext contém contexto e fontes, não uma resposta natural gerada. `request_id` vem da Knowledge API; `correlation_id` vem da LUMA. Conteúdo recuperado é `UNTRUSTED_DATA` e não concede permissão de executar.

## Testar

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:LUMA_TEST_KNOWLEDGE_WORKSPACE='D:\cerebro do gestor'
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=runtime/test-local
.\.venv\Scripts\python.exe audit_workspace.py
```

Use basetemp exclusivo: pytest limpa essa pasta. Sem `LUMA_TEST_KNOWLEDGE_WORKSPACE`, o teste real de integração é pulado explicitamente; os testes unitários usam transportes simulados. Na validação da entrega o teste real **foi executado**, com dois servidores temporários em portas loopback efêmeras e comparação de oito assuntos. Somente o harness importa a aplicação Knowledge para iniciar o serviço aprovado; o backend LUMA não lê arquivos do Cérebro. Bytecode externo desabilitado. Testes locais de sockets precisam de autorização fora da restrição de rede do sandbox Windows.

## Escopo e documentação

- [Arquitetura, segurança e limites](docs/ARQUITETURA.md)
- [Contratos futuros e políticas](docs/CONTRATOS_FUTUROS.md)
- [Contratos JSON Schema](contracts/models.json) e [OpenAPI](contracts/openapi.json)
- [Relatório da Fase 7A](reports/FASE_7A_RELATORIO_NUCLEO_LUMA.md)

Somente knowledge.read executa. Aprovações, sessões e aprendizado têm modelos/serviços internos e armazenamento limitado em memória, sem endpoints administrativos. Ações externas, promoção canônica, agentes, Gemini, ADK, Calendar, Tasks, OAuth, frontend e deploy não foram implementados. Parar ao final desta fase; próxima exige autorização específica.
