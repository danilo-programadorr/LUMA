# Fase 7D — Gemini model adapter da LUMA

Data: 2026-10-21. Responsável: Codex. Workspace: D:/projetos/luma. **Candidata 0.4.0rc1; implementação e validação local concluídas, aprovação integral BLOQUEADA por ausência de credencial Gemini.** Nenhuma chamada real ao modelo foi executada. Produção não verificada. Confiança alta nas evidências locais explicitamente descritas; comportamento do Gemini real NÃO CONFIRMADO.

## 1–3. Baseline, SDK e ModelProvider

Baseline LUMA 0.3.0: b9c435c6c5d55833c9027a74bc45c81c0da57741, 156 testes. HEAD e árvore limpa confirmados; audit_workspace.py VERIFIED antes das mudanças. Branch local codex/fase-7d-gemini-model-adapter. Autorização preservada em AUTORIZACAO_FASE_7D.txt.

SDK oficial google-genai **2.32.0**, fixado com dependências em backend/requirements/lock.txt. google-generativeai e google-adk ausentes. pip check sem inconsistências. ModelProvider é contrato desacoplado; GeminiModelProvider gerencia worker e GeminiAdapter concentra import/chamada SDK. A camada de negócio não importa Google. Evidência: backend/app/generation.py, model_provider.py, backend/model_worker/adapter.py e FASE_7D_DEPENDENCIAS.json.

## 4–6. Isolamento, ambiente e secrets

Processo dedicado por geração, shell=False, Python -I, protocolo JSON com correlação, frame 256 KiB de entrada/128 KiB de saída, timeout, limpeza e máximo de dois workers simultâneos. Ambiente montado explicitamente com GEMINI_API_KEY e SYSTEMROOT/WINDIR. Não herda tokens administrativos/runtime/Knowledge, DB URL, proxies, PATH ou PYTHONPATH. Worker não recebe Store/repositories nem importa módulos de banco/control plane.

A chave é lida somente de ambiente, distinta dos tokens locais, não persistida. Backend filtra segredos conhecidos antes/depois do modelo; o worker descarta stderr e desabilita logs. Audit usa metadados, sem prompt/resposta integral. ModelInputContext é o único conteúdo fornecido à geração. Testes verificam sentinelas em entrada/saída, erros, DB, audit, logs e OpenAPI.

Limite importante: processo separado não equivale a sandbox do SO. Worker roda sob o mesmo usuário; não foram criadas ACLs, container, conta isolada ou bloqueio geral de filesystem/rede. Não há código gerado pelo modelo executado localmente. Essa limitação permanece explícita para revisão futura.

## 7–11. Adaptador, modelo, instrução e contratos

SDK usa resposta JSON Schema, tools vazio e automatic_function_calling desabilitado. Nenhuma função executável é registrada. Defaults testados sem rede: temperature 0,2, max_output_tokens 2048, timeout 30s e attempts=1. Configuração fica no servidor; tetos detalhados em docs/MODEL_LAYER_7D.md.

**Modelo realmente usado em rede: nenhum.** gemini-test é somente identificação de fixture determinística. Opção candidata futura: gemini-3.8-flash, identificada como estável e compatível com structured outputs na documentação oficial consultada em 2026-10-21; disponibilidade/acesso da conta não foram testados. Não há nome de modelo de produção espalhado no código.

Fontes: [SDK oficial](https://googleapis.github.io/python-genai/), [saída estruturada](https://ai.google.dev/gemini-api/docs/structured-output), [modelo candidato](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).

System instruction luma-system-1 versionada em backend/model_worker/system_instruction.txt. Define LUMA sem privilégios de owner, UNTRUSTED_DATA, incerteza, projeto ativo e proibição de alegar execução. Seu conteúdo não aparece no OpenAPI. ModelInputContext contém mensagem, sessão/projeto/locale, janela limitada e KnowledgeContext autorizado. ModelDecision rejeita extras e mantém propostas sem autoridade. Campos de aprovação, grants, unlock e identity override não são aceitos.

## 12–14. Grounding, citações e endpoint

POST /v1/conversation/turn é humano, com owner bearer e Idempotency-Key. Runtime token não é exposto ao navegador. Backend valida sessão, humano/runtime, interseção de projetos, grants, revogação, estado e tool antes da consulta e novamente após geração. Troca de projeto pelo texto do modelo não modifica active_project_id.

Todo turno de Meu Gestor consulta Knowledge nesta primeira política conservadora. Sem Knowledge, a resposta falha fechada sem chamar modelo, inclusive para saudação. Não há leitura direta do Cérebro, ranking duplicado ou envio de corpus inteiro. KnowledgeContext permanece UNTRUSTED_DATA.

Citações são validadas pelo par document_id/chunk_id e retornam a fonte original. Fonte inventada ou ausência de citação quando há contexto e não há pedido de esclarecimento gera erro. Answer preserva warnings/confidence/freshness, marca produção não verificada e separa confiança do modelo. Controle adicional rejeita expressões comuns de execução falsa; não é garantia universal de compreensão semântica. A garantia de zero execução vem da inexistência do executor e da policy.

## 15–18. Continuidade, persistência, propostas e learning

Migração explícita 0003 acrescenta conversation_windows e conversation_requests, preservando 0001/0002 intactas. Dois novos grants por interseção: conversation.turn humano e runtime.model.generate runtime; nenhum admin adicionado ao runtime.

Janela por sessão: até quatro pares e 8.000 caracteres, expiração de uso em 24h. Não persiste conversa ilimitada; metadados de requisição guardam hash/status/correlação, sem conteúdo. Categorias próprias NO_AUTO_DELETE, preview sem purge. Contexto vencido deixa de ser enviado, sem alegar exclusão física automática. Lease serializa a mesma sessão; sessões distintas permanecem separadas. Chave repetida retorna 409, sem nova geração/custo; não guarda cache ilimitado de respostas.

Propostas passam por validação de tool/capability/parâmetros. Backend define ID, risco, origem MODEL_PROPOSED, correlação e status DENIED em toda proposta disparada pelo modelo nesta fase de zero execução. Campos enviados pelo modelo não autorizam execução. Learning permanece PROPOSED, só persiste se houver grant runtime.learning.propose; sem grant é sugestão explicitamente não persistida. Sem promoção/alteração do Cérebro.

## 19–23. Erros, timeout, uso, safety e injection

Erros separados: MODEL_TIMEOUT, MODEL_UNAVAILABLE, MODEL_AUTH_ERROR, MODEL_RATE_LIMIT, MODEL_INVALID_RESPONSE, MODEL_ERROR e MODEL_SAFETY_REJECTION. Mensagens brutas/stack traces do fornecedor não chegam à API. EOF, frame excessivo/inválido, correlação incorreta, crash e timeout encerram worker e falham fechados. Admin/Knowledge continuam funcionando. Readiness registra último estado sem chamadas pagas em /health.

Uma única tentativa, sem retry automático nem no SDK; evita repetição em auth/schema/safety/quota e custo incerto. Limites de entrada, contexto, saída e timeout são server-side. Audit de geração registra provider/model/prompt-version, principals, sessão/projeto, correlação, resultado, tokens quando disponíveis e latência do turno incluindo recuperação. Sem preço calculado, billing ou cobrança implementados.

Safety do fornecedor é complementar. Testes de injection usam contexto contendo comandos de elevação, mas confirmam ausência de grants/approvals/execução. Isso valida controles do backend; resistência linguística de Gemini real permanece não verificada.

## 24–30. Evidências

- FASE_7D_TESTES_CANDIDATA.txt: **206 testes aprovados, zero skips**, 162,70s; um aviso de depreciação Starlette/httpx. Os 156 anteriores foram preservados; expectativas de revision/retention/grants foram atualizadas para a migração aditiva, sem retirar cobertura.
- FASE_7D_TESTES_INTERMEDIARIOS.txt: primeira suíte ampliada com 201 aprovados, preservada como histórico.
- FakeModelProvider determinístico: conversa, continuidade, citações, secrets, propostas, learning, indisponibilidade, limites, replay, revogação durante geração e concorrência.
- SDK google-genai real com HTTP simulado: serialização de schema, ausência de tools executáveis, uso e mapeamento de 401/403/429/503/400 sem rede nem retry.
- Worker sintético em processo real: crash, JSON inválido, frame excessivo, timeout, ID incorreto, EOF, ambiente sanitizado, recuperação e limpeza.
- FASE_7D_KNOWLEDGE_REAL.json: oito categorias por HTTP real, owner/runtime equivalentes à Knowledge direta e conversa fake usando Knowledge real. Não é teste Gemini real.
- FASE_7D_RESTART_REAL.json: dois processos distintos, saída limpa, sessão/janela e metadados conversacionais preservados junto de grants/revogações/controles.
- FASE_7D_MIGRACAO_BACKUP.json: banco operacional 0002→0003, linhas anteriores preservadas, 29 grants e sete políticas; backup anterior e posterior, restauração temporária com integrity_check=ok e todas as tabelas/cadeia iguais.
- FASE_7D_AUDITORIA.json: auditoria final e hashes de fontes protegidas; migrações 0001/0002 comparadas ao baseline, DB/backups ignorados, nenhuma alteração no app/Cérebro.
- FASE_7D_GEMINI_REAL.json: **BLOCKED_NEEDS_CREDENTIAL, zero casos reais executados**. Nenhum resultado fake foi apresentado como resposta real do Gemini.

## 31–34. Versão, commit, limites e decisão

Backend 0.4.0rc1, sem declarar 0.4.0 plenamente validado. Knowledge API 0.1.0, Cérebro 0.6.0 e Engine 1.4.0 preservados. Commit local candidato: `feat: adiciona adaptador Gemini e conversa da LUMA`; hash do commit que contém este relatório registrado em runtime/phase-7d-commit-receipt.json e informado ao proprietário. Nenhum remote/push/deploy.

Pendência exata: disponibilizar LUMA_GEMINI_API_KEY (ou alias GEMINI_API_KEY) no ambiente do processo validador, LUMA_MODEL_PROVIDER=gemini e LUMA_GEMINI_MODEL explícito. Use Read-Host -AsSecureString conforme README; não envie chave pelo chat. Execute `python -m backend.validate_gemini` para os oito cenários autorizados; o programa não faz chamada real na ausência de chave. Chave definida em outro terminal não é herdada automaticamente pelo processo atual. O teste real e a revisão de naturalidade/incerteza devem passar antes de promoção a 0.4.0.

Limitações adicionais: separação de processo sem sandbox de SO, sem garantia universal de detecção de segredo desconhecido ou falsidade em linguagem natural, schema e orçamento ainda não exercitados contra o serviço Gemini real, ambiente local SQLite sem validação de produção. Audit tamper-evident continua sem âncora externa. Conversas limitadas podem conter texto privado autorizado, protegido pelas permissões locais e fora do Git; não há criptografia de aplicação.

**Parada na Fase 7D.** Não aprovada integralmente enquanto Gemini real estiver bloqueado. Não iniciar 7E/ADK, agentes, Calendar, Tasks, frontend, voz ou deploy. Requisito visual/voz existente foi preservado. Próxima recomendação é concluir a validação Gemini isolada com credencial; só depois avaliar autorização específica para 7E.


## Correcao dirigida de 2026-10-21 — diagnostico seguro

Responsavel: Codex. Base: 273d536b843172df03eff4918d83d8483f9ac64b, backend 0.4.0rc1.

Evidencia fornecida pelo proprietario: chamada direta google-genai ao modelo gemini-3.8-flash retornou OK no PowerShell configurado. O relatorio FAILED anterior foi preservado em FASE_7D_GEMINI_REAL_ANTES_CORRECAO.json. Essa evidencia nao determina qual etapa falhou dentro da LUMA.

Causa comprovada da ausencia de diagnostico (confianca alta, inspecao de backend/validate_gemini.py na base): except Exception descartava a excecao; a primeira resposta HTTP diferente de 200 virava assert sem codigo; cases_executed contava apenas casos aprovados; servers_stopped era incondicional. A causa da falha da chamada real permanece NAO CONFIRMADA. Nao ha evidencia para atribui-la a credencial, rede, modelo ou generation config.

Correcao: etapas explicitas, codigos e tipos seguros, protocolo do worker com diagnostico de campos e valores enumerados, distincao entre HTTP 400, MAX_TOKENS e schema invalido; contagem de tentativas e aprovados separada; cleanup verificado; historico dos relatorios preservado. Mensagens brutas de excecao, prompts, respostas e credenciais nao sao persistidos. Temperatura, limite, MIME, hash do schema e versao da instrucao sao registraveis sem conteudo sensivel.

A chamada minima 'Responda somente OK' usa o mesmo GeminiModelProvider, Python -I, ambiente restrito, GeminiAdapter e ModelDecision estruturado; nao introduz modo permissivo. Apos esse probe passam os oito cenarios existentes pelo backend HTTP. O modelo permanece sem autoridade para executar ferramentas. Parametros e schema de geracao nao foram relaxados nem alterados sem evidencia de incompatibilidade.

Execucao neste processo: credential_present=false; validador retorna BLOCKED_NEEDS_CREDENTIAL na etapa configuration. Isso descreve somente o processo Codex, nao invalida a evidencia do PowerShell do proprietario. O proprietario confirmou que executara o validador no PowerShell configurado e fornecera o JSON sanitizado. Nenhuma integracao Gemini real nova foi comprovada nesta correcao.

Decisao atual: NO-GO para promover 0.4.0rc1. Validacao real e causa raiz pendentes. Nenhuma nova fase autorizada ou iniciada.

Comando para o PowerShell que ja possui a credencial:

```powershell
Set-Location 'D:\projetos\luma'
.\.venv\Scripts\python.exe -m backend.validate_gemini
Get-Content -LiteralPath '.\reports\FASE_7D_GEMINI_REAL.json' -Raw
```

O resultado atual e os historicos distinguem a falha original da execucao sem credencial neste processo. O manifesto FASE_7D_HASHES_ENTREGA.json continua sendo evidencia da candidata original; nao foi reescrito para ocultar a correcao.

Validacao local da correcao: suite original 206 passed (180.79s); suite ampliada 213 passed, zero skips (182.83s), exit code 0. Sete testes direcionados do validador final tambem passaram (2.89s). Um aviso de deprecacao Starlette/httpx ja conhecido. Auditoria FASE_7D_AUDITORIA_CORRECAO.json: VERIFIED, sem erros; fonte main@9fe7fd3a69a537f9e67953b7028e64c676a48547 e repositorio financeiro limpos.


## Correcao dirigida de grounding — 2026-10-21

Responsavel: Codex. Baseline 9dc9aec2dae8822f8fc0742135c98eb10e862c5d, versao 0.4.0rc1. Evidencia fornecida pelo proprietario e confirmada no arquivo local: Gemini gemini-3.8-flash real, probe do worker aprovado, geracao tentada; greeting reprovado por MODEL_MISSING_CITATION, 1 caso executado / 0 aprovados. Resultado preservado em FASE_7D_GEMINI_REAL_ANTES_GROUNDING.json. Status: causa confirmada, confianca alta, implementacao e relatorio concordantes. Nao atribuido a chave, modelo, rede ou startup.

Causa: a politica anterior consultava Knowledge em todos os turnos e exigia citacao pela presenca de resultados, inclusive na saudacao. O rotulo first generation era impreciso para essa validacao posterior; agora erros de citacao e afirmacao de execucao sao classificados response validation.

Correcao geral: GroundingRequirement backend-owned NONE/REQUIRED. Lista pequena de expressoes completas permite NONE apenas em conversa social clara. Mensagens mistas, follow-ups, assuntos factuais e qualquer ambiguidade seguem REQUIRED por padrao. Nao ha IDs de eval, nomes de casos ou excecao por greeting na politica. OPTIONAL nao foi necessario. A entrada HTTP nao aceita override; o modelo recebe a decisao como dado do backend.

NONE evita Knowledge e remove historico factual do input; nao cria KnowledgeContext ficticio. Autorizacao, grants, revogacoes e sessao continuam vigentes. A indisponibilidade do servico externo Knowledge permite conversa social. REQUIRED exige consulta atual antes do modelo e falha fechado se indisponivel; historico nunca substitui fontes. Uma conversa social intermediaria nao transforma o proximo follow-up em NONE.

Citacoes sao sempre comparadas aos pares document_id/chunk_id das sources autorizadas. Sem fontes fornecidas, qualquer citacao e invalida. REQUIRED sem citacao falha, inclusive com contexto vazio, salvo pedido de esclarecimento sem fatos reconhecido por formatos conservadores server-side. O boolean needs_clarification do modelo sozinho nao libera resposta factual. Instruction versionada luma-system-2. Schema ModelDecision, modelo, credenciais e parametros Gemini preservados; contratos de input atualizados.

Limitacao explicita: a lista conversacional e conservadora, nao semantica geral. Mensagens sociais nao reconhecidas podem exigir Knowledge. Formulacoes de esclarecimento fora dos formatos conhecidos exigem fonte ou sao rejeitadas. Essa escolha evita dispensar grounding por inferencia ambigua.

Validador mantem a parada no primeiro cenario falho e preserva historico. Nao houve tuning de outros cenarios nem mudanca de modelo. Promocao permanece condicionada a suite Gemini real completa; nao ha autorizacao para nova fase.


Resultado desta correcao: 79 testes direcionados aprovados (68.92s); suite completa 242 passed, zero skips, zero falhas (184.42s), mantendo os 213 anteriores e acrescentando 29. Um aviso de deprecacao Starlette/httpx permanece. Evidencias: FASE_7D_TESTES_GROUNDING.txt e .xml. Auditoria: VERIFIED, sem erros, em FASE_7D_AUDITORIA_GROUNDING.json.

Apos a suite local, python -m backend.validate_gemini foi executado neste processo e retornou BLOCKED_NEEDS_CREDENTIAL, failure_stage=configuration, safe_error_code=CREDENTIAL_NOT_IN_THIS_PROCESS, credential_present=false, real_model_tested=false, 0 casos executados / 0 aprovados. Nao se trata de nova falha em um cenario Gemini. A credencial do PowerShell do proprietario nao foi alterada nem lida de outro processo. O resultado real anterior (probe aprovado, greeting falhou, 1/0) esta preservado separadamente; nao demonstra o comportamento apos esta correcao.

Versao final desta rodada: 0.4.0rc1. Decisao: NO-GO para promocao da Fase 7D enquanto a execucao real dos oito cenarios nao completar. Correcao validada localmente; confirmacao real pendente no PowerShell configurado, usando gemini-3.8-flash. Ao surgir outra falha de cenario, preservar o JSON e parar para revisao, sem tuning cego. Nenhuma Fase 7E iniciada.


## Diagnostico dirigido de unauthorized_action — 2026-10-21

Base 033e4fb33eb075e8943a25d0fde4cf7c29771cef. Responsavel: Codex. Evidencia real anterior preservada em FASE_7D_GEMINI_REAL_ANTES_PROVIDER_DIAGNOSTICO.json: greeting/project/follow_up/malicious_context aprovados; unauthorized_action falhou com MODEL_ERROR; 5 executados / 4 aprovados. A credencial e o worker funcionaram nessa rodada.

Causa classificada: contrato local de entrada, antes do provider (categoria D: configuracao/contrato interno; nao falha demonstrada do fornecedor). Estado REPRODUCED, confianca HIGH. A janela duravel da execucao real contem quatro turnos, serializados em 2846 caracteres; ModelInputContext.session_summary limita a 2000. A retencao da janela admite ate 8000 por padrao. O teste de construcao com esse mesmo historico reproduz ValidationError/string_too_long em session_summary. Somente tamanho, campo e tipo foram registrados, sem prompt/resposta. A janela persistida ja prova que a retencao admitiu esses 2846 caracteres. Evidencia e hash do DB: FASE_7D_CAUSA_LOCAL_MODEL_ERROR.json.

O except generico de ConversationService convertia essa excecao em MODEL_ERROR. O provider.diagnostic mostrava o sucesso do turno anterior, pois a nova chamada sequer chegava a provider.generate. Agora a falha recebe MODEL_INPUT_SCHEMA_INVALID / model input validation; o validador limpa o diagnostico entre turnos. Para esta causa: provider_status=null, finish_reason=null, block_reason=null, retryable=false, provider_called=false. Nenhum erro HTTP, safety ou schema de saida foi demonstrado no quinto turno.

Escopo implementado: diagnostico e classificacao segura. Limites de historico, modelo, chave, parametros de geracao, schema ModelDecision, grounding, citacoes, Knowledge, politica e system instruction permanecem inalterados. A incompatibilidade de tamanho foi diagnosticada, nao corrigida nesta rodada. Nao foi adicionado retry.

Mapeamento adicional: HTTP 400 -> MODEL_INVALID_REQUEST; 401/403 -> MODEL_AUTH_ERROR; 408 -> MODEL_TIMEOUT; 429 -> MODEL_RATE_LIMIT; 5xx -> MODEL_UNAVAILABLE; outros erros API reconhecidos -> MODEL_PROVIDER_ERROR. Retryable=true somente para timeout/transitorios identificados, sem repetir chamada automaticamente. Fallback desconhecido permanece MODEL_ERROR. Finish reason, prompt block reason, categorias de safety e tipo/codigo do provider usam vocabularios fechados. JSON/schema invalido registra response_received, schema_validation=false e codigo seguro, sem detalhes brutos. A fronteira do worker valida novamente os campos. response_received indica resposta HTTP/SDK recebida, inclusive resposta de erro; schema_validation indica especificamente validacao de ModelDecision, quando aplicavel.

Modo dirigido: --case unauthorized_action executa somente esse caso pela LUMA HTTP em sessao nova, com texto original. --diagnose-unauthorized executa esse caso primeiro e so prossegue para a suite completa se passar; cada relatorio anterior e preservado. Como o isolado nao contem a janela cumulativa, seu sucesso nao prova que a falha anterior era transitoria. Nao ha substituicao de Gemini por fake nos modos reais.


Validacao desta rodada: 46 testes direcionados aprovados (18.15s); suite completa 266 passed, zero skips, zero falhas (193.08s), preservando os 242 anteriores. O teste anterior de HTTP 400 teve a expectativa atualizada para MODEL_INVALID_REQUEST conforme o mapeamento solicitado; nenhum teste removido. O aviso Starlette/httpx ja conhecido permanece. Evidencias em FASE_7D_TESTES_PROVIDER_DIAGNOSTICO.txt/.xml. Auditoria VERIFIED, sem erros.

Depois dos testes, o comando python -m backend.validate_gemini --diagnose-unauthorized foi executado. Resultado: BLOCKED_NEEDS_CREDENTIAL em configuration, credential_present=false neste processo Codex; caso isolado nao executado, 0/0; suite real completa nao iniciada. Isso nao invalida a credencial do PowerShell do proprietario. Nenhuma nova resposta Gemini foi obtida. O ultimo ensaio real continua sendo 5/4, preservado. Status do provider, finish_reason e block_reason da tentativa atual sao null; nao atribuir bloqueio de configuracao a erro do fornecedor.

Decisao: NO-GO, versao 0.4.0rc1. Diagnostico local concluido e causa reproduzida; incompatibilidade de tamanho mantida para revisao. Nao promover nem iniciar outra fase. Para executar no PowerShell configurado: python -m backend.validate_gemini --diagnose-unauthorized. Esse modo para em qualquer falha e conserva relatorios anteriores.
