# Contratos futuros — sem integrações executáveis

Status: CONTRATOS/REQUISITOS, NÃO IMPLEMENTADOS COMO INTEGRAÇÃO. Fonte: autorização Fase 7A em `../reports/AUTORIZACAO_FASE_7A.txt`. Versão 0.1.0, 2026-10-20, verificador Codex; confiança alta quanto ao registro do requisito, nenhuma evidência de operação externa.

## Ferramentas e capabilities

Knowledge Client: ENABLED_LOCAL, knowledge.read. Todos os seguintes: PLANNED, enabled=false.

| Ferramenta | Capabilities previstas |
|---|---|
| Google Calendar | calendar.read, availability, create, update, delete, reminders, invite; write é categoria reservada |
| Google Tasks | tasks.read, create, update, complete, reopen, organize, delete; write é categoria reservada |
| GitHub | github.read, github.write |
| Firebase | firebase.read, firebase.deploy |
| Codex | codex.execute |
| Analytics | analytics.read |
| Google Ads / Meta | ads.manage |
| PC Runner | pc.execute |

Calendar deverá consultar agenda/horários livres, criar/alterar/cancelar compromissos, configurar lembretes e acompanhar calendário da conta Google sincronizada com celular. Outros participantes/convites exigem confirmação. Nenhum OAuth ou chamada Google.

Tasks deverá atender pendências pessoais/de projetos, prazos, listas, criação, edição, conclusão, reabertura, organização e exclusão. Nenhuma chamada Google.

## Política conceitual AUTO / CONFIRM / DENY

Leituras knowledge, calendar, availability, tasks, github, firebase e analytics: AUTO, sempre sujeitas a capability, tool habilitada e controles. Calendar create/update/reminders e Tasks create/update/complete/reopen/organize: AUTO somente quando pedido explicitamente pelo OWNER; sem esse sinal humano confiável, CONFIRM. Exclusões Calendar/Tasks, convites/participantes, github.write, firebase.deploy, codex.execute, ads.manage e pc.execute: CONFIRM. Capability desconhecida ou categoria write não concretizada: DENY. Todas as ferramentas externas continuam desabilitadas independentemente desse resultado conceitual.

ActionRequest contém action_id, principal_id, project_id, tool_id, capability, intent, parameters, risk_level, approval_requirement, status e created_at. ApprovalRecord é separado e específico, com approval_id/action_id/principal_id, decision, timestamp/expires_at, scope e reason opcional. Não há permissão eterna ou reaproveitamento entre ações. Schemas em `../contracts/models.json`.

## Memory, Knowledge e aprendizado

MEMORY: preferências/contexto pessoal permitido e histórico operacional mínimo. Não há memória conversacional persistente implementada. KNOWLEDGE: fatos canônicos por projeto, consultados pela API oficial. LEARNING CANDIDATE: afirmação ainda não promovida, com source, project, claim, evidence, confidence, status e data.

Fluxo obrigatório futuro: experiência → candidato → evidência → validação → aprovação quando necessária → write-back futuro. Neste núcleo só se registra PROPOSED com evidência; VALIDATED/REJECTED/PROMOTED são vocabulário de contrato, não endpoints de promoção. promote() sempre rejeita WRITE_BACK_DISABLED. Inferência da LUMA nunca vira verdade canônica automaticamente. Não misturar memória, conhecimento e candidato.

## Agentes, modelo e framework

Nove registros PLANNED: LUMA — Gestora Geral; Produto; Desenvolvimento; Codex / Engenheiro de Código; QA; Segurança; Dados & Analytics; Growth & Marketing; Conteúdo & Social. A abertura da autorização menciona oito agentes, mas a lista explícita da etapa 25 enumera nove: adotada a lista específica, sem criar agentes executáveis.

LUMA será a única orquestradora principal. Especialistas não poderão autoatribuir privilégios, chamar ferramentas sem capability, trocar projeto ativo, ignorar approval policy ou promover aprendizado sozinhos. Registro não cria instância, processo ou agente de IA.

ModelProvider é apenas Protocol Python com porta generate(KnowledgeContext). Provedor futuro: **Google Gemini API**; nenhum cliente real, nenhuma chamada e nenhum motor OpenAI instalado/implementado para LUMA. Framework futuro: **Google ADK**, ainda não instalado. Contratos internos não importam ADK e devem permitir substituição. Google Login, Next.js/TypeScript, Gemini, ADK, Calendar/Tasks e agentes exigem fase e autorização próprias.
