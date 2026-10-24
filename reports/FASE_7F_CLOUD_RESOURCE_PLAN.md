# Fase 7F — plano de recursos antes de criação

Data: 2026-10-24. Responsável: Codex. Estado: PROPOSTA NÃO APLICADA.
Baseline: 62b2afa074966c6a7c3886a2d2d4730cbce23442, Backend 0.5.0.
Evidências de preflight: FASE_7F_CLOUD_PREFLIGHT.json.
Não há autorização de criação faturável nem recursos criados nesta rodada.

## Projeto e região

Projeto existente LUMA: gen-lang-client-0178588873, número 347540226289,
ACTIVE, billing habilitado. Somente generativelanguage.googleapis.com está
habilitada. Projeto e região padrão do gcloud não estão definidos; comandos
devem sempre passar o projeto explicitamente. Nenhuma configuração foi alterada.

Região proposta: southamerica-east1. A documentação pública lista São Paulo
para Cloud Run, Cloud SQL PostgreSQL, Artifact Registry, Cloud Scheduler e
Cloud Tasks. Isso não comprova quotas, permissões ou políticas da organização.

## Configuração proposta para piloto privado

| Recurso | Configuração inicial proposta | Custos e limites |
| --- | --- | --- |
| Artifact Registry | Um repositório Docker regional, política de retenção a revisar | Armazenamento e transferência; não escala a zero em armazenamento |
| Cloud Run Control Plane | Uma instância máxima, zero mínima, 1 vCPU, 512 MiB, cobrança por requisição, concorrência 8 | Computação por uso, rede e logs; limites deverão ser confirmados por teste |
| Cloud Run Web | Uma instância máxima, zero mínima, 1 vCPU, 512 MiB, cobrança por requisição, concorrência 8 | Computação por uso, rede e logs; zero mínima permite cold starts |
| Cloud SQL PostgreSQL | PostgreSQL 17, Enterprise, zonal, db-f1-micro, SSD inicial 10 GiB, sem HA, crescimento automático inicialmente desligado | Somente piloto; shared core sem SLA. Instância ativa, disco e backups geram custos contínuos. Não escala automaticamente a zero |
| Secret Manager | Segredo de conexão e chave de assinatura cloud; versões mínimas e rotação definida antes do deploy | Versões ativas e acessos; nenhuma chave Gemini/Codex/privada do dispositivo |
| Identity Platform | Google login, domínio HTTPS exato, um Owner vinculado por enrollment seguro | Cobrança depende do produto/provedor/uso vigente; não presumir gratuidade |
| Cloud Scheduler | No máximo um job autenticado por OIDC para manutenção/expiração | Cobrança por job conforme tabela vigente |
| Cloud Tasks | Não criar inicialmente; adicionar somente se necessidade comprovada | Operações e rede se adotado; não necessário para polling básico |
| IAM/service accounts | Contas distintas para control plane, web e scheduler; permissões mínimas | Sem chaves JSON exportadas; custo dos serviços utilizados permanece |
| Logging | Retenção e limites explícitos antes do deploy; logs sanitizados | Ingestão/retenção podem gerar custo; sem prompts completos, tokens ou PII desnecessária |

Esses valores são propostas para dimensionamento, não recursos observados.
Disponibilidade de machine type, quotas e compatibilidade do conector serão
verificadas antes de solicitar criação. Não há estimativa monetária fechada:
o pricing depende da região, moeda, SKU, consumo, disco, backup e transferência.
Consultar tabelas/calculadora oficiais na aprovação; não usar preços de Iowa
como se fossem preços de São Paulo.

Conexão SQL por conector oficial autenticado por IAM, sem authorized networks
públicas; topologia e necessidade de egress privado devem ser fechadas antes do
deploy. Pool inicial máximo 5 conexões, overflow 0 por instância.
Banco novo e seed limpo: nunca copiar banco local.
APIs propostas: run, sqladmin, artifactregistry, secretmanager,
identitytoolkit, cloudscheduler e iam; cloudtasks apenas se adotado.
Cloud Build só se escolhido explicitamente como mecanismo de build.
Habilitar API também é uma mutação e não foi executado.

## Gate de custo e limpeza

Antes de criação, revisar este plano com a implementação/testes locais e obter
resposta explícita à pergunta:
“AUTORIZAR CRIAÇÃO DOS RECURSOS CLOUD DA FASE 7F?”
Este documento registra a pergunta exigida; não constitui aprovação nem
solicitação antecipada para ignorar os gates locais.

Infraestrutura deverá ter scripts idempotentes com projeto/região explícitos,
modo de inspeção, inventário e recibos. Terraform não foi encontrado.
Limpeza proposta: pausar Scheduler; desabilitar entrada nos serviços do piloto;
remover serviços Cloud Run e imagens dedicados; revogar IAM dedicado; destruir
segredos e Cloud SQL somente após aprovação específica de perda de dados,
retenção/exportação decididas e verificação de que pertencem ao piloto.
Nunca excluir o projeto existente ou recursos Gemini preexistentes.
Parar Cloud Run não elimina custos de SQL, armazenamento, backups e logs.
Nenhum script de criação ou limpeza foi executado.

## Gate local que precede o deploy

7F-A ainda não implementado. Não foram encontrados Docker/PostgreSQL locais.
A escolha de PostgreSQL isolado, Docker ou servidor dedicado está pendente
do proprietário. Testes reais devem cobrir migrações, persistência/restart,
idempotência, concorrência de claims, revogação e integridade da auditoria.
Sem essa evidência, não avançar para gates posteriores nem promover versão.

## Referências oficiais consultadas em 2026-10-24

- https://docs.cloud.google.com/run/docs/locations
- https://docs.cloud.google.com/sql/docs/postgres/locations
- https://docs.cloud.google.com/artifact-registry/docs/repositories/repo-locations
- https://docs.cloud.google.com/scheduler/docs/locations
- https://docs.cloud.google.com/tasks/docs/locations
- https://cloud.google.com/run/pricing
- https://cloud.google.com/sql/pricing
- https://docs.cloud.google.com/sql/docs/postgres/instance-settings
- https://www.postgresql.org/download/windows/
