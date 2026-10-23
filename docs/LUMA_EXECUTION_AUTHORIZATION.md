# Autorização de execução

2026-10-23. Control plane é autoridade canônica. ActionRequest é proposta; ApprovalRecord é decisão humana; ExecutionAuthorization delimita ações; Job é ocorrência concreta; ExecutionRecord registra o resultado. O origin da autorização é HUMAN_DIRECT, criado somente pela rota autenticada HUMAN_OWNER com capabilities administrativas atuais. Runtime, modelo, ADK e executor não aprovam.

CanonicalActionEnvelope fixa projeto, ferramenta, operação, recurso, destino, parâmetros, execution_target, target_device_id e allowed_paths. Hash também cobre risco calculado pelo backend, policy_version e constraints de agenda. Alteração material falha AUTHORIZATION_SCOPE_MISMATCH. Parâmetros de elevação são rejeitados. Recursos locais têm deny-by-default; o contrato de paths não liga acesso real ao filesystem nesta fase.

ONE_SHOT exige quota 1 e envelope exato. BOUNDED_WINDOW e RECURRING_POLICY usam template exato (nenhum wildcard), validade e quota; recurring exige intervalo >=60s. LOW aceita os três; MEDIUM aceita one-shot/recurring com constraints; HIGH somente one-shot, confirmação administrativa adicional, expiração até 10 minutos; CRITICAL unattended negado. Validade máxima inicial 30 dias. Schedule é janela explícita; mudar destino/device ou ampliar janela exige nova autorização. Quota é persistente, com reserva antes do efeito e consumo após reconciliação.

A sessão humana pode terminar. Execução revalida estado RUNNING, revogações, tool, projetos/principais ativos, prazo, policy version, template e grants atuais do owner e executor. Kill switch prevalece sobre qualquer autorização. Capabilities humanas admin.actions.manage e admin.approvals.manage também precisam continuar válidas. O bearer local é identidade de desenvolvimento; não serve como autenticação final de internet.

POST /v1/action-requests, POST /v1/action-requests/{id}/authorize, GET /v1/execution-authorizations, GET detalhe, POST revoke e POST /v1/jobs. Mutação requer Idempotency-Key; HIGH requer X-Admin-Confirmation. Modelo não escolhe hash/idempotência final. Device enrollment/heartbeat têm autenticação distinta. Nenhuma rota executa ferramenta arbitrária.
