# Readiness de deployment — 2026-10-23

NO-GO para deploy nesta fase (fora de escopo). Arquitetura híbrida recomendada em docs/LUMA_ALWAYS_ON_ARCHITECTURE.md e plano em docs/LUMA_7F_DEPLOYMENT_PLAN.md. Prontos para testes locais: persistência SQLite, leases, autorização independente da sessão, identidade de dispositivo e canal outbound. Pendentes para internet: identidade humana forte, enrollment/rotação hardened, isolamento de SO, PostgreSQL, secret store, operação/observabilidade cloud e revisão de custo. Nenhuma ferramenta mutável externa habilitada. Não confundir conclusão local com produção.


Fechamento 0.5.0: GO / CONCLUIDA para o escopo da Fase 7E, com ADK + Gemini real 10/10 e execucao local em sandbox. O NO-GO para deploy acima permanece: cloud/frontend/integracoes reais nao foram autorizados nem implementados no fechamento. Fase 7F nao iniciada.
