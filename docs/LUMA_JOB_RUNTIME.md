# Jobs, scheduler e executor

2026-10-23, Codex. Migração 0004 aditiva preserva 0001–0003 e cria autorizações, jobs, registros/reconciliação, tasks/workflows, devices e ledger sandbox. Repository SQLAlchemy separa armazenamento; SQLite é política local, não arquitetura cloud final.

Scheduler separado torna SCHEDULED elegível como READY. LOCAL_DEVICE offline permanece WAITING_FOR_DEVICE e volta a ser validado após heartbeat. CONDITION tem interface interna por condition_id, sem integração externa; IMMEDIATE e SCHEDULED_AT funcionam; recurring cria próxima ocorrência após conclusão dentro de quota/validade. SKIP é padrão para atraso além da resolução de 1s; RUN_LATE_WITHIN_GRACE exige graça explícita até 3600s; REQUIRE_REAUTHORIZATION bloqueia. Autorizações vencidas não voltam a executar quando a máquina retorna.

Executor separado adquire lease com transação serializada no banco (30s). READY→LEASED→RUNNING→SUCCEEDED. Lease vencido antes de efeito volta a elegível; RUNNING vencido exige reconciliação, não retry cego. Reserva de quota, última revalidação e efeito do TestTool são uma transação local. Depois, outro commit registra SUCCEEDED. Crash entre efeito e resultado é reconciliado pelo ledger sem duplicação. Dois processos concorrentes disputam o mesmo lease; testes provam somente um efeito. FAILED/BLOCKED/CANCELLED/EXPIRED são terminais; cancelamento não finge desfazer efeito já iniciado.

TestTool existe somente quando injetado pelo harness de testes; não integra registry de produção. Executor público recusa qualquer adapter externo. Não há exactly-once universal: providers futuros precisam idempotência nativa ou ledger + reconciliation, e podem deixar resultado UNKNOWN para revisão. Nenhum retry automático genérico de side effect. A transação local não comprova atomicidade com APIs externas.

Executores rejeitam ambiente com OWNER, ADMIN, RUNTIME, Knowledge ou Gemini tokens. Identidade SERVICE_EXECUTOR possui somente executor.jobs.execute. Processo local confiável lê o DB sem tokens humanos; permissions de SO ainda são a fronteira contra código arbitrário sob o mesmo usuário.
