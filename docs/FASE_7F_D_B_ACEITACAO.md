# Aceitação local 7F-D-B

Estado: implementação e regressões em curso; não é declaração de aceitação real.

Launcher: scripts/start_remote_tasks_local.ps1 -Mode server. Mantém PostgreSQL local existente, auth Google, biblioteca e pesquisa configuradas; habilita somente TestTool. Biblioteca permanece suspensa. Não inicia modelo, Gemini Live, Codex ou executor operacional.

Após prontidão técnica: Owner autentica na LUMA /tasks, confirma identidade, permite somente testes sintéticos no PC ACTIVE existente se necessário, cria ACTION_ORIENTED/record e revisa a proposta em /approvals. Aprovar deve produzir um único job; executar somente pelo device_agent oficial já vinculado. Confirmar resultado/timeline e refresh. Repetir com rejeição; outra tarefa com revogação antes de executar, inclusive device offline. Nenhum novo enrollment sem gate Owner.

Registros sanitizados: IDs, estados, decisão/hash, recent-auth sem token, autorização/job internamente, contagem de efeito sintético, dispositivo, expiração, correlação e auditoria. Nenhuma credencial ou documento privado em reports.

Sem commit/push/merge/tag/release/deploy. Não iniciar 7F-E ou VPS.
