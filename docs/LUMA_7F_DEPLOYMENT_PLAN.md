# Plano futuro 7F — não iniciado

Exige autorização nova. Nenhum recurso pago ou deploy foi criado na 7E.

1. Definir região, orçamento e limites de consumo; revisar residência/retenção de dados.
2. Login humano forte, sessão web, step-up e MFA/passkey; substituir bearer local como autenticação de internet.
3. PostgreSQL/Cloud SQL, backups e testes de migração/concorrência; nenhuma SQLite efêmera como storage final.
4. Cloud Run Control Plane, ADK worker isolado e Cloud Executor com IAM separado; Cloud Scheduler/Tasks como disparadores, banco como autoridade. Avaliar Agent Runtime sem bypass do ModelProvider.
5. Secret Manager com CredentialRef; enrollment/rotação/revogação de device. Local Executor Windows outbound, sem porta pública; futura instalação como serviço com identidade de SO separada e paths permitidos.
6. OAuth do próprio owner para futuras Google APIs. Offline access requer consentimento adequado, access_type=offline e refresh token protegido, conforme https://developers.google.com/identity/protocols/oauth2/web-server#offline . Só guardar referência no banco. Não implementado nesta fase.
7. Pilotar uma ferramenta por autorização específica com idempotência/reconciliation e rollback; Calendar/Tasks/Gmail continuam desabilitados até aprovação.

Calendar planejado: read/availability/create/update/delete/reminders. Tasks: read/create/update/complete/reopen/organize/delete. Codex futuro: proposta→aprovação→autorização exata com workspace→Job LOCAL_DEVICE→device autorizado→CLI restrita→ExecutionRecord. Browser precisa policy de URL/ação; desktop HIGH. Não habilitar shell genérico.

Sem deploy, tarefas locais exigem PC ligado e processos locais ativos. Não se afirma operação com PC desligado. Depois de cloud always-on, somente tarefas CLOUD poderão funcionar sem o PC; tarefas PC_REQUIRED esperarão o device.
