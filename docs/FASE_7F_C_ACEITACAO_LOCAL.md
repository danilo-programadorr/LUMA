# Aceitação local 7F-C — pendente de interação do Owner

Data: 2026-10-26. Backend 0.6.0rc1; Web 0.1.0-rc.1.

Control Plane: http://127.0.0.1:8770. Web: http://localhost:5173.
PostgreSQL: local isolado, porta 55432, schema 6. Backup anterior à migration em runtime/postgresql-backups, protegido por ACL e ignorado pelo Git. O arquivo de backup contém dados locais e não deve ser anexado a relatórios.

1. Abra a Web, entre com a conta Owner já vinculada e acesse Dispositivos.
2. Use Confirmar identidade novamente se necessário. Clique Adicionar dispositivo.
3. No PowerShell, execute:

```powershell
Set-Location 'D:\projetos\luma'
.\.venv\Scripts\python.exe -m device_agent enroll
```

4. Cole o código da Web apenas na entrada oculta. Não envie o código ao chat.
5. Compare o fingerprint completo do PowerShell com o cartão. Aprove somente se forem iguais, dentro de cinco minutos da solicitação.
6. Execute `.\.venv\Scripts\python.exe -m device_agent run`. Aguarde ONLINE e atualize a página.
7. Pare com Ctrl+C. Aguarde mais de 45 segundos e confirme OFFLINE.
8. Execute run novamente. Confirme ONLINE com o mesmo fingerprint, sem novo enrollment.
9. Clique Autorizar teste sintético uma única vez. A evidência no banco deve comprovar um claim e um resultado lógico, sem efeito externo.
10. Revogue na Web e confirme bloqueio no próximo pedido do agente. A identidade revogada não deve ser reutilizada; novo enrollment exige nova aprovação.

A coleta técnica sanitizada deve verificar eventos, estado do job, identidade estável e revogação; não substituir a interação Owner por identidade de teste. Não registrar private key, enrollment code, tokens ou dados pessoais desnecessários.

Serviços locais foram iniciados para esta aceitação. Não há serviço automático Windows nem deploy. Encerrar os processos registrados em runtime/7fc-services.json ao fim da aceitação, verificando sua identidade antes de encerrá-los.

Gate permanece NOT_GO_UNTIL_REAL_ACCEPTANCE. Não iniciar 7F-D-A nem executar Codex real. Não realizar commit ou push.
