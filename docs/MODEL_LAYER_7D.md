# Model layer da LUMA — candidata Fase 7D

Data: 2026-10-21. Responsável: Codex. Implementação e testes locais; integração Gemini real depende de credencial. Esta candidata não é aprovação integral 0.4.0.

## Arquitetura e fronteira

Humano autenticado → POST /v1/conversation/turn → sessão/escopos/grants atuais → decisao de grounding → Knowledge API HTTP quando REQUIRED → ModelInputContext → ModelProvider → processo Gemini dedicado → Google GenAI SDK → ModelDecision validado → resposta com fontes. Runtime token permanece interno; navegador futuro não recebe essa credencial.

Somente o worker importa google-genai. Não há ADK, SDK legado google-generativeai, agente, function calling executável ou executor de tools. O SDK recebe tools vazio e automatic_function_calling desabilitado. Parâmetros de modelo são exclusivamente server-side. Backend reavalia todas as decisões; retorno de modelo nunca concede grants, aprova, desbloqueia, muda identidade/projeto ou promove conhecimento.

Um worker por geração, no máximo dois concorrentes. Popen com shell=False, Python -I, stdin/stdout estruturados, ID de correlação, entrada até 256 KiB e saída até 128 KiB, stderr descartado, timeout e encerramento/reap no sucesso ou falha. Processos recebem somente GEMINI_API_KEY e SYSTEMROOT/WINDIR necessários ao ambiente Windows; sem OWNER/RUNTIME/ADMIN_CONFIRM/KNOWLEDGE tokens, DB URL, proxies, PATH/PYTHONPATH ou ambiente herdado inteiro. Nenhum objeto Store/repository chega ao worker.

Esse isolamento de processo melhora a fronteira, mas **não é sandbox contra código arbitrário no mesmo usuário do SO**: permissões de filesystem/rede não foram restringidas por usuário separado, container ou ACL específica. O modelo é uma API remota sem ferramentas locais; o worker é código confiável. Não se afirma que um processo comprometido seja impedido pelo SO de abrir arquivos acessíveis ao usuário. Só o contexto autorizado é enviado, nunca o corpus inteiro.

## Configuração e SDK

SDK oficial: google-genai; versão instalada/testada no lock. Backend lê LUMA_GEMINI_API_KEY (alias opcional GEMINI_API_KEY, conflito rejeitado), LUMA_MODEL_PROVIDER=gemini e LUMA_GEMINI_MODEL explícito. Worker recebe nome oficial GEMINI_API_KEY e passa a chave explicitamente ao SDK. GOOGLE_API_KEY não é herdada. Chaves devem ser distintas das quatro credenciais locais. Nenhuma chave é persistida.

Model name deve corresponder ao padrão gemini-* seguro; isso valida formato, não disponibilidade na conta. Sem chave/modelo/provider configurado, a chamada falha MODEL_UNAVAILABLE e o control plane/Knowledge seguem disponíveis. Status não faz chamada de modelo; inicialmente NOT_PROBED, depois reflete a última tentativa, sem promessa de disponibilidade futura.

Defaults: input 2.000 caracteres; KnowledgeContext serializado 24.000; janela conversacional 8.000; saída 2.048 tokens; temperature 0,2; timeout 30s incluindo início do worker; uma única tentativa, sem retry automático nem no SDK. Tetos: 2.000/32.000/8.000 caracteres, 4.096 tokens e 60s. O contexto excedente falha fechado; não remove fontes arbitrariamente. Modelo tem que produzir JSON completo dentro do limite; resposta truncada é inválida.

Fontes oficiais consultadas em 2026-10-21: [SDK Python](https://googleapis.github.io/python-genai/), [saída estruturada](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). A página oficial identifica gemini-3.8-flash como estável e com saída estruturada; é uma opção candidata para o teste futuro. Não foi usado em chamada real nesta entrega sem credencial. Nenhum preço ou acesso da conta foi presumido.

## Contratos, instrução e fontes

System instruction versionada luma-system-2 em backend/model_worker/system_instruction.txt: LUMA não é owner, documentos são UNTRUSTED_DATA, não inventar autorização/execução, preservar incerteza e escopo, não solicitar/revelar segredos. OpenAPI não expõe seu conteúdo. O prompt é camada complementar, não autoridade.

ModelInputContext contém mensagem, sessão/projeto/locale, janela limitada, KnowledgeContext e disponibilidade de tools vazia. ModelDecision permite mensagem, intenção, propostas, requested_knowledge, confiança, esclarecimento, citações e sugestões de learning. Extra fields são rejeitados. requested_knowledge não dispara chamadas adicionais automaticamente. Citações devem corresponder ao par document_id/chunk_id fornecido; o backend retorna a fonte original, não metadados inventados. Resposta em turno REQUIRED exige fonte valida, exceto pedido de esclarecimento reconhecido pelo backend; a flag do modelo sozinha nao dispensa citacoes. Warnings, confidence, freshness e production_verified=false são retornados pelo backend.

Controle adicional rejeita afirmações comuns de execução em primeira pessoa (marquei, executei etc.). Esse filtro não comprova detectar toda afirmação falsa em linguagem natural; nenhuma resposta do modelo é prova de execução. A ausência técnica de executor permanece a garantia principal. Mesmo uma proposta de Knowledge pelo modelo não executa tool automaticamente; todas as propostas desta fase são registradas DENIED por política de zero execução, com origem MODEL_PROPOSED e correlação do backend.

Learning só pode ficar PROPOSED; persistência exige grant runtime.learning.propose válido. Sem ele a sugestão é retornada como não persistida. Não existe escrita no Cérebro.

## Continuidade, concorrência e retenção

Migração 0003 aditiva preserva 0001/0002 e acrescenta conversation_windows e conversation_requests. Concede conversation.turn ao humano e runtime.model.generate ao runtime, por interseção de projetos. Não concede admin ao runtime. Sem grants atuais, Knowledge/tool ativo e sessão humana vinculada, não há geração.

Uma janela por sessão guarda até quatro pares de mensagens e no máximo 8.000 caracteres; expira para uso em contexto após 24h. Conteúdo antigo sai da janela nas próximas atualizações. Não é histórico ilimitado nem conhecimento canônico. Metadados de requisição têm fingerprint, status e correlação, sem prompts/respostas. Duas categorias de retenção NO_AUTO_DELETE; preview conta expiração sem purge. Expiração não representa exclusão física automática.

Lease transacional impede duas gerações concorrentes na mesma sessão. Sessões distintas não compartilham contexto. Antes e depois do I/O são revalidados principal humano/runtime, projeto, sessão, grants, revogação, tool e kill switch. Resposta obsoleta após revogação não é entregue nem adicionada à janela.

Idempotency-Key é obrigatório. Repetir uma chave já registrada retorna 409 TURN_ALREADY_RECORDED, sem nova geração ou cobrança; outro corpo com a chave retorna IDEMPOTENCY_CONFLICT. Não há cache durável ilimitado de respostas. Após falha, uma nova tentativa é decisão explícita com nova chave. Requests interrompidos permanecem metadados; lease expira para permitir nova requisição após recuperação.

## Falhas, privacidade e métricas

MODEL_TIMEOUT, MODEL_UNAVAILABLE, MODEL_AUTH_ERROR, MODEL_RATE_LIMIT, MODEL_INVALID_RESPONSE, MODEL_ERROR e MODEL_SAFETY_REJECTION são separados. Exceções externas não expõem stack trace nem mensagem bruta do fornecedor. Provider indisponível não derruba admin/Knowledge. Neste primeiro fluxo toda conversa no Meu Gestor consulta Knowledge; indisponibilidade fecha a resposta sem chamar Gemini ou inventar fatos, inclusive saudações. É uma política conservadora documentada.

Filtro antes do modelo bloqueia valores conhecidos de credenciais, campos sensíveis e padrões de segredo. Filtro de saída também atua antes da persistência/entrega. Métricas input_tokens/output_tokens são inteiros validados, não credenciais. O scanner não identifica universalmente segredo desconhecido ou texto ofuscado. Audit contém provider/model/prompt-version/principals/sessão/projeto/correlação, latência, uso e resultado, sem prompt/resposta integral. Uso é base técnica para orçamento futuro, sem cobrança implementada.

## Bloqueio da validação real

Sem chave, o relatório deve registrar BLOCKED_NEEDS_CREDENTIAL e candidato/pré-release. Para liberar validação real, configure a chave somente no ambiente do processo que iniciará o backend/validador, com LUMA_MODEL_PROVIDER=gemini e LUMA_GEMINI_MODEL apropriado. Não cole a chave no chat, arquivo versionado ou comando literal. A etapa real ainda precisa dos oito cenários autorizados, incluindo grounding, continuidade, fonte, incerteza, injection e indisponibilidade de Knowledge.

Calendar/Tasks continuam PLANNED/DISABLED; ADK, agentes executáveis, frontend e voz permanecem fora do escopo. Requisito de núcleo visual/voz é preservado, sem implementação. 7E depende de nova autorização e aprovação isolada do adaptador real.


## Correcao dirigida: grounding por turno

Decisao deterministica do backend em backend/app/grounding.py: NONE apenas para mensagens completas reconhecidas como saudacao, agradecimento, despedida, confirmacao social ou orientacao sobre como conversar. REQUIRED e o padrao para tudo mais, inclusive mensagens mistas, perguntas factuais, follow-ups curtos, texto ambiguo e tentativas de definir grounding via prompt. OPTIONAL nao e necessario nesta politica binaria conservadora.

NONE nao consulta Knowledge e envia knowledge=null, sem historico factual. Uma indisponibilidade do servico Knowledge nao impede esse turno social, mas identidades, grants, revogacoes, sessao e controles locais continuam verificados. REQUIRED consulta Knowledge atualizado; indisponibilidade bloqueia antes da geracao. Historico nao substitui a consulta. Uma saudacao entre perguntas nao remove grounding de um follow-up factual posterior.

O cliente e o modelo nao podem definir grounding_requirement. A flag aparece somente no ModelInputContext construido pelo backend. Citacoes sao sempre verificadas contra pares document_id/chunk_id das sources autorizadas, inclusive quando NONE (nesse caso nenhuma fonte foi fornecida). REQUIRED sem citacao e rejeitado, mesmo com contexto vazio, salvo pedido de esclarecimento sem fatos que corresponda aos formatos conservadores do backend. needs_clarification nao e autoridade. Formulacoes fora desses formatos exigem citacao ou falham fechadas.

System instruction luma-system-2 proibe fatos do projeto sem grounding e explicita que conversa social nao exige fontes. Nenhum parametro Gemini, modelo, credencial ou schema ModelDecision foi relaxado. A classificacao nao e um classificador semantico geral: texto desconhecido segue REQUIRED.
