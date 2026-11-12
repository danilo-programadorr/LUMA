# Roteiro de aceitaÃ§Ã£o real â€” ainda bloqueado

NÃ£o executar chamadas reais atÃ© aprovaÃ§Ã£o financeira especÃ­fica e confirmaÃ§Ã£o de apresentaÃ§Ã£o/retencÃ£o compatÃ­vel com requisitos Google. Ver reports/FASE_7F_D_A_SEARCH_COST_PREFLIGHT.md. NÃ£o criar API, chave, billing ou recurso cloud para contornar gate.

ApÃ³s liberaÃ§Ã£o dos gates: iniciar PostgreSQL local; executar scripts/start_research_local.ps1 -Mode migrate (faz backup protegido); iniciar -Mode server; iniciar Web em localhost:5173. A migration do banco Owner real ainda nÃ£o foi aplicada nesta fase.

Owner entra com Google, abre Devices, cria novo enrollment. Usar PowerShell separado sem credenciais de CP/DB: .\.venv\Scripts\python.exe -m research_agent enroll. Novo arquivo protegido runtime/research-agent/identity.db; jamais apagar/sobrescrever/reactivar a identidade revogada da 7F-C. Confirmar novo fingerprint e aprovar. No painel de pesquisa, selecionar explicitamente novo PC e Autorizar WEB_RESEARCH (recent-auth).

Somente apÃ³s gate financeiro: configurar no processo runtime a Gemini key existente, LUMA_RESEARCH_REAL_APPROVED e limite de chamadas autorizado; nÃ£o registrar valores. LUMA_RESEARCH_ATTRIBUTION_APPROVED somente apÃ³s validaÃ§Ã£o tÃ©cnica da apresentaÃ§Ã£o, nÃ£o como dispensa dos requisitos do provider. Reutilizar Knowledge API local e token existente se necessÃ¡rio ao hÃ­brido. Nenhuma credencial Owner vai para runtime.

Executar research_agent run e verificar ONLINE. Testar consulta atual, tÃ©cnica oficial, cientÃ­fica e URL Context; registrar somente status, uso, fontes e timestamps. HÃ­brido: pergunta interna do Meu Gestor + pergunta pÃºblica genÃ©rica separada; nÃ£o enviar texto interno ao provider. InformaÃ§Ã£o interna de LUMA requer fonte prÃ³pria registrada e permanece indisponÃ­vel, sem inventar fatos.

Parar agente, observar OFFLINE, enviar consulta atual e verificar WAITING_FOR_DEVICE. Reiniciar mesma identidade; aceitar somente se request ainda vÃ¡lido. Guardar evidÃªncia sanitizada de resposta e fontes na UI, concorrÃªncia/sem duplicaÃ§Ã£o, cache policy, uso/custo. NÃ£o simular resposta factual especÃ­fica como aceitaÃ§Ã£o real.

Ao concluir, deixar novo device ACTIVE para prÃ³xima fase; encerrar processos de teste ao terminar salvo instruÃ§Ã£o explÃ­cita. NÃ£o revogar o Ãºnico PC real para provar revogaÃ§Ã£o (jÃ¡ coberta em dispositivos sintÃ©ticos). NÃ£o iniciar Private Library/Remote Approvals/voz nem fazer commit/push/deploy.


Correção de atribuição (2026-10-27): autorização financeira recebida, máximo acumulado seis chamadas. Usar scripts/run_research_acceptance.ps1 -Mode enroll/status/run no PowerShell com a chave Gemini existente. Não enviar a chave ao chat, não persistir em arquivo. Run exige precheck PASS e hashes atuais, preserva flags anteriores ao encerrar e usa ledger durável runtime/research-google-acceptance-usage.json. Reiniciar não concede outras seis chamadas. Cada tentativa é reservada antes de enviar, depois registra somente uso/contagem/latência/erro; contagem desconhecida permanece UNKNOWN. Qualquer falha do provider interrompe a aceitação; não tentar outra consulta para contornar atribuição.

A UI deve ser vista ao vivo pelo Owner: somente metadados operacionais ficam persistidos. Refrescar descarta a apresentação e não repete a pesquisa. Seis perguntas públicas propostas estão em reports/FASE_7F_D_A_REAL_ACCEPTANCE_PLAN.json; URL Context usa o campo de URL selecionada. Não inserir contexto proprietário. O runtime para ao consumir a sexta chamada acumulada ou ocorrer falha. A etapa de dispositivo e a chave no processo do PowerShell exigem interação do Owner; não são simuladas por testes de browser.


Atualização operacional 2026-10-29: o banco Owner já está no schema7 e o dispositivo de pesquisa já foi vinculado/aprovado. Não repetir migration ou enrollment para esta correção. Preservar runtime/research-agent/identity.db e a chamada já registrada. Após precheck final PASS, reiniciar somente research_agent no PowerShell com a chave já configurada, usando scripts/run_research_acceptance.ps1 -Mode run. Atualizar a LUMA, selecionar o mesmo PC e enviar uma consulta pública do roteiro; se aparecer Abrir resultado Google, abrir em até30s. Artefato incompatível interrompe novamente a aceitação. Correção e limites em reports/FASE_7F_D_A_REAL_SEARCH_PRECHECK.md.
