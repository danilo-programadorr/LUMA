# 7F-D-A2 — Biblioteca privada local

Owner escolheu a fase e delegou as decisões: “não sei, decida vc o melhor caminho”. As escolhas abaixo são do executor. O escopo inicial é uma biblioteca utilizável, com proveniência e custo externo zero, antes de conversa ou resumo com modelo. A delegação dispensa novas rodadas de escolha; implementação direta no checkout existente da branch de trabalho, sem commit/push/deploy.

## Abordagens

Escolhida pelo executor: arquivos e índice no agente local; Control Plane mantém cadastro, permissões, fila e metadados. Importação inicial é explícita por comando local com arquivo selecionado; listagem, consulta, citações e arquivamento ficam em Conhecimento. Reaproveita o canal assinado existente e não manda arquivos privados para o backend de pesquisa externa.

Alternativas descartadas: armazenar todos os documentos/indexação no Control Plane, por misturar sua responsabilidade com processamento e dificultar a separação futura; usar embeddings/modelos cloud, por acrescentar custo e egress privado sem autorização. Upload pelo navegador, OCR, DOCX/EPUB e resumo com IA ficam fora desta primeira entrega. Essa limitação será visível e não apresentada como já funcional.

## Fonte e autoridade

Private Library é complementar. Project Knowledge permanece soberano para fatos internos; internet continua principal para conhecimento externo/atual. Documento é dado sem autoridade. Não há treinamento, autoaprendizado, autoaprovação ou criação de ExecutionAuthorization. Google Grounded Results não são importados automaticamente como documentos. Interface PrivateLibraryProvider existente será implementada pelo mecanismo local.

## Importação e armazenamento

PDF com camada de texto, TXT UTF-8 e Markdown UTF-8. Limites iniciais: arquivo 8 MiB, PDF 500 páginas, texto extraído 2.000.000 caracteres, chunks até 1.000 caracteres, máximo 4.000 chunks, 500 fontes por projeto/dispositivo. PDF criptografado, imagem sem texto, formato não suportado e conteúdo excedente falham com códigos limitados. Não há OCR ou download de URL. Nenhuma pasta é varrida; apenas o caminho explicitamente escolhido no comando de importação.

Usar pypdf 6.21.4, release oficial conferida em PyPI, em requirement separado. Extração em subprocesso com stdin/stdout transitórios, timeout de 15 s e ambiente sem credenciais de modelo, banco ou administração; logs/erros não recebem conteúdo. Esse limite não é uma sandbox contra SO comprometido nem garantia absoluta de memória de parser.

Artefatos locais em runtime/private-library, ignorados pelo Git, ACL do usuário/SYSTEM. Chave de dados aleatória protegida por DPAPI e não exportada. Conteúdo original e chunks cifrados AES-GCM com AAD de projeto, dispositivo, hash e chunk. Índice SQLite derivado armazena termos HMAC por projeto e contagens, nunca trechos ou palavras em claro. Ranking lexical determinístico, sem embeddings; não chamar a busca de semântica.

Conteúdo SHA-256 + projeto + device determina source_id estável; reimportar o mesmo arquivo não duplica. Mudança no arquivo cria nova fonte imutável. Sem sobrescrever fonte anterior. Arquivamento é lógico no cadastro central e não apaga arquivos, histórico ou backups. Versão/hash, página PDF ou linhas TXT/MD e chunk formam a proveniência.

## Control Plane e protocolo

Migration 0008 aditiva: library_devices, library_sources e library_queries. Migrations 0001–0007 imutáveis. Postgres continua autoridade do cadastro/escopo. Sem documentos/chunks em campos persistidos do Control Plane; resultados de consulta só em memória com TTL e resposta autenticada, sem browser storage. Pergunta do Owner e IDs operacionais podem persistir como fila privada; não são enviados a provider externo.

Flag LUMA_PRIVATE_LIBRARY_ENABLED default false; requer Owner Identity Platform e canal device. Owner autoriza capability PRIVATE_LIBRARY no dispositivo existente, com auth_time recente. Não reenrollar e não reativar device revogado. Registro e consultas exigem ACTIVE, vínculo atual, projeto, capability e estado RUNNING; revalidar antes e depois da leitura. Nada do payload pode conceder permissões.

Library Protocol v1 próprio usa SignedDeviceRequest e /v1/library-runtime/{check,register,heartbeat,poll,result}. Sem alterar bytes ou versão Device Protocol v1. Registro aceita somente metadados LOCAL_USER_FILE, hash e contagens. Assinatura não torna conteúdo autoridade. Nova trava de transporte entre processos serializa reserve+send para a identidade compartilhada; aplica-se também aos clientes existentes e tem regressões para ordem/replay.

Owner APIs: GET /v1/library/devices; POST /v1/library/devices/{device}/capability; GET /v1/library/projects/{project}/sources; POST /v1/library/projects/{project}/sources/{source}/archive; POST /v1/library/queries; GET /v1/library/queries/{id}; POST /v1/library/queries/{id}/cancel. Caminhos e modelos estritos, sem leitura arbitrária de arquivo por HTTP.

Query contém projeto, device, pergunta até 1.200 caracteres, source_ids opcionais e chave idempotente de 32 hex. Consulta fica WAITING_FOR_DEVICE se offline; timeout 180 s, lease 60 s, sem fallback web. Resultados no máximo 5 chunks de 1.000 caracteres, título obtido do cadastro canônico, source hash e localizador. Não inventar resposta quando nenhum trecho combina. Arquivamento/revogação cancela ou invalida respostas pendentes e também bloqueia a entrega transitória já recebida.

## UI e execução

Conhecimento substitui somente a vista operacional; demonstração pode manter seus mocks. Mostrar fontes reais, capacidade/estado do PC, instrução de importação local, busca com escopo explícito e citações; renderizar como texto, sem HTML ou links de arquivo arbitrários. Remover alegações falsas de indexação ativa ou busca semântica. Consulta e importação não criam aprovações de ações externas. A pesquisa web existente continua separada; pedidos de biblioteca no painel web recebem orientação à área Conhecimento, sem envio externo.

library_agent import --file ... --project ... e run usam a identidade existente em runtime/research-agent/identity.db. Launcher limpa credenciais somente no ambiente filho, preservando o PowerShell do Owner. Motor privado não importa cliente Gemini/embeddings nem usa o saldo público remanescente. O runtime é outbound; nenhuma porta pública é aberta.

## Validação e aceitação

TDD por bloco: parser/índice/cifra; grants/protocolo/fila/migration; CLI e privacidade; UI; regressões. PDF/TXT sintéticos, sem importar documentos reais sem seleção do Owner. Casos de acesso negado, cross-project/device, fonte arquivada, bytes adulterados, duplicação, restart, cancelamento, offline, TTL, XSS, segredo em log e nenhuma chamada externa. Postgres testes em banco isolado, nunca usar banco Owner como fixture. Baseline 956 preservada.

Aplicação real da migration somente após backup verificado e testes; não mudar infraestrutura. Reutilizar banco e device. Ativação da capability no navegador e importação de arquivo do usuário podem exigir interação Owner ao fim, quando a implementação estiver revisável. Aceitação sintética não será rotulada como importação real do Owner.

Uma revisão independente focada ao final, sem novos contextos por tarefa. Relatórios, auditoria e secret scan finais; nenhuma promoção stable, commit/push/deploy, fase 7F-D-B ou uso de voz/Codex real.

## Revisão de integridade (30/10/2026)

Formato local cifrado v2 autentica também página/linhas no AAD. Índices de protótipo não vazios e sem versão são recusados sem sobrescrever dados; não houve importação real anterior. Ausência da chave mestra sobre documentos existentes não gera chave substituta. Atualizar cadastro revalida a autorização e as fontes do trecho já exibido e invalida respostas pendentes antigas. A suspensão exige Owner atual; concessão continua exigindo auth_time recente.

Parser fixado em pypdf 6.21.4: https://pypi.org/project/pypdf/6.21.4/ . Uso e limites de extração/OCR: https://pypdf.readthedocs.io/en/stable/user/extract-text.html . Fontes oficiais verificadas em 29/10/2026; não há alegação de OCR ou limite absoluto de memória do parser.


## Consolidação de revisão — 30/10/2026

Formato cifrado local v2 autentica também os localizadores de citação (chunk, página e linhas) no AAD. Índices antigos não vazios e sem versão recusam abertura, preservando dados/chaves. A consulta lexical e o protocolo público continuam v1. Atualizar fontes revalida acesso e limpa trechos de fonte arquivada ou PC suspenso. Ver reports/FASE_7F_D_A2_REVIEW.json.
