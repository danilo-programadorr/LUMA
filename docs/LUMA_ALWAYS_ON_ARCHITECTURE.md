# Arquitetura híbrida always-on

Recomendação de arquitetura, não infraestrutura provisionada. 2026-10-23, Codex.

Web no celular → HTTPS → Control Plane → banco durável → scheduler → filas separadas por ExecutionTarget → Cloud Executor ou Local PC Executor outbound autenticado. Em paralelo: Control Plane → Orchestrator → ADK isolado → ModelProvider validado. Autorizações, grants, revogações, jobs e auditoria permanecem no banco canônico da LUMA, nunca em session ADK.

| Opção | Vantagens | Limitações / custo operacional |
|---|---|---|
| Cloud Run para Control Plane e workers | Controle das fronteiras e imagens, serviços/jobs/worker pools; integração IAM/observabilidade | Banco e identidade separados; capacidade e consumo precisam orçamento; disco efêmero não é banco durável |
| Agent Runtime para ADK | Runtime de agentes gerenciado e integração com observabilidade/sessões | Não substitui autorização/queue/executor; adaptar ponte custom ModelProvider requer validação adicional; custo e retenção precisam revisão |
| Híbrido Cloud Run + Agent Runtime | Separa control plane e runtime gerenciado | Mais identidades, protocolos e superfície operacional; não necessário para primeiro deploy |

Recomendação inicial 7F: Control Plane e worker ADK em serviços/imagens separados no Cloud Run; PostgreSQL/Cloud SQL privado; Secret Manager; Cloud Scheduler para despertar reconciliação/eligibilidade e Cloud Tasks para despacho cloud com idempotência. Local Executor no Windows faz outbound para tarefas LOCAL_DEVICE. Agent Runtime permanece alternativa após medir benefício e provar preservação da fronteira ModelProvider. Pub/Sub é útil para sinalização/eventos, não autoridade de execução. Scheduler próprio com DB continua referência canônica, inclusive se eventos forem repetidos.

Não usar SQLite efêmero em Cloud Run. Jobs, leases e atomicidade devem ser revalidados em PostgreSQL. Tracing usa correlation/task/workflow/job/authorization IDs, sem payload integral. IAM mínimo para cada serviço; credenciais externas por referências, nunca coluna plaintext. Não há preço calculado: comparar consumo medido, instâncias mínimas, storage, rede e observabilidade na autorização 7F.

Fontes oficiais consultadas: https://cloud.google.com/run/docs/overview/what-is-cloud-run ; https://cloud.google.com/agent-builder/agent-engine/overview ; https://cloud.google.com/tasks/docs/dual-overview . Conclusão de escolha é avaliação técnica da LUMA, não recomendação oficial do fornecedor.


## Estado oficial na 0.5.0

Fase 7E concluida; Fase 7F nao iniciada. Executor local incorporado a arquitetura e validado com TestTool em sandbox. Cenario futuro: Owner fora de casa -> LUMA Web no celular -> autorizacao humana -> Control Plane cria Job -> Local PC Executor Windows recebe via outbound -> PC ligado e elegivel executa conforme autorizacao. LOCAL_DEVICE exige PC ligado; offline fica WAITING_FOR_DEVICE. Nao existe fallback silencioso para cloud ou outro dispositivo. Web remota, cloud e integracoes externas ainda nao implantadas. Recomendacao 7F existente preservada, sem implementacao neste fechamento.
