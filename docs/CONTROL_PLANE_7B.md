# Control plane local — política 7B

Data 2026-10-21, versão 0.2.0, verificador Codex. A superfície administrativa autentica bearer e exige a capability específica persistida; role textual OWNER não substitui a verificação. Principal inicial local-owner recebe grants explícitos no bootstrap. Não há endpoint para trocar principal, alterar grants, fornecer path de DB ou URL de Knowledge arbitrários.

| Rotas GET /v1/admin | Capability |
|---|---|
| state | admin.status.read |
| projects | admin.projects.read |
| tools | admin.tools.read |
| agents | admin.agents.read |
| actions, actions/{id} | admin.actions.read |
| approvals, approval-requests | admin.approvals.read |
| revocations | admin.revocations.read |
| sessions | admin.sessions.read |
| learning | admin.learning.read |
| audit | admin.audit.read |

| Mutação | Capability / política |
|---|---|
| POST state | admin.state.manage; saída LOCKED também admin.state.unlock, confirmation UNLOCK_LUMA e segredo adicional |
| PATCH projects/{id} | admin.projects.manage; só name/status/enabled, nenhum endpoint/URL novo |
| POST tools/{id}/enable ou disable | admin.tools.manage; enable só Knowledge; ferramentas externas não habilitáveis |
| POST revocations | admin.revocations.manage; escopo atual, principal autenticado, tool opcional, capability conhecida, reason e expires_at opcional |
| POST actions | admin.actions.manage; proposta sem execução; requisito calculado no backend |
| POST actions/{id}/transition | admin.actions.manage; somente cancelamento de estados não terminais permitidos |
| POST approvals/{action_id}/decision | admin.approvals.manage + X-Admin-Confirmation + HUMAN_DECISION + hash scope |
| POST approvals/{approval_id}/consume | admin.approvals.manage + X-Admin-Confirmation; apenas consumo de validação, nunca execução |
| POST sessions e sessions/{id}/close | admin.sessions.manage; projeto autorizado e status válido |
| POST learning e learning/{id}/status | admin.learning.manage; criar PROPOSED ou mudar para VALIDATED/REJECTED; PROMOTED impossível |

Todas exigem Idempotency-Key. Chave é armazenada somente em hash escopado pelo principal; fingerprint vincula operação, target e payload. Repetição idêntica retorna snapshot original sem efeito novo; conflito explícito 409. Autorização/confirmador são rechecados antes do replay. Para conhecer o estado atual, usar GET.

## Aprovação humana e limites

O canal administrativo requer credencial própria de confirmação, distinta dos bearers LUMA e Knowledge, mantida em LUMA_ADMIN_CONFIRM_TOKEN e apresentada em X-Admin-Confirmation. Esse segredo adicional não é persistido/logado. Sem ele, decisão de approval e saída de LOCKED são negadas. Campo approved=true ou alteração de principal/capability no payload é rejeitado.

Esta é uma declaração autenticada de decisão administrativa local, não autenticação forte de produção/MFA nem prova de presença humana. Nunca entregar bearer administrativo e segredo de confirmação a uma futura camada LLM. Nesta fase não há LLM conectado, executor ou ferramenta que possa chamar a administração autonomamente.

Scope de approval é hash dos campos estáveis da ação, incluindo parâmetros e principal/projeto; mudanças de status não alteram o fingerprint. APPROVE só de PROPOSED/WAITING_APPROVAL; segunda decisão com outra chave falha. Consumo exige action APPROVED, scope intacto, mesmo principal/projeto, prazo vigente, não consumida, estado RUNNING e sem revogação. Consumo muda action para CANCELLED e execution_performed=false. Isso testa single-use sem simular SUCCEEDED nem executar ferramenta desabilitada. DENIED/CANCELLED são terminais; não existe caminho HTTP para EXECUTING/SUCCEEDED/FAILED nesta fase.

Revogações são por principal autenticado/projeto/capability e tool opcional. Revogação expirada deixa de aplicar por prazo absoluto; nenhuma aprovação ganha prazo novo. Revogação de capability administrativa de um escopo também bloqueia a operação administrativa agregada correspondente. Não existe endpoint genérico de remoção da revogação: recuperação exigirá política específica futura ou expiração previamente definida.

## Dados e auditoria

Segredos conhecidos da instância e padrões de credenciais são rejeitados antes de qualquer armazenamento administrativo. Chaves como password/token/secret/authorization/api-key/cookie em parâmetros são negadas. Este filtro não é detector universal de segredos desconhecidos: operadores devem usar referências mínimas e dados sintéticos, não colar documentos/conversas/finanças completas.

Audit persiste somente IDs/metadados/evento/resultado/correlação. Contexto Knowledge, query, intent/parameters e reason não entram no audit. Reason/claim/evidence/parameters fazem parte das entidades necessárias e passam pelo filtro; não são logs. Não há endpoint de edição de audit. A proteção não cobre um administrador com acesso direto ao arquivo DB; arquivos/backups não são cifrados por este núcleo.

Bootstrap só ocorre em schema vazio e numa transação; reinício reabre estado existente. Registro parcial/incompatível falha fechado. Configuração inicial persistida inclui política de histórico/packages; ambiente não a sobrescreve. Alterar endpoint estático sem reconciliação do registro persistido provoca falha de rota; nenhum endpoint administrativo aceita uma URL para contornar isso.

Calendar/Tasks e demais tools externos continuam PLANNED/DISABLED, Gemini/ADK apenas contratos, nove agentes PLANNED. Persistência não concede autorização para integrá-los.
