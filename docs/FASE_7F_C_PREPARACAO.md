# Fase 7F-C — preparação técnica

Data: 2026-10-25. Responsável: Codex. Status: proposta baseada nos itens completos 0–71; não é implementação nem evidência de funcionamento. O anexo termina no início do item 72. A continuação foi solicitada antes de presumir critérios finais.

## Base preservada

Workspace D:/projetos/luma; HEAD dc85fa894e2ad99325ef77a937d0f7a8f2a38fe7; branch codex/fase-7f-remote-control-local-executor. 7F-B_OWNER_AUTH_VALIDATED, 673 testes únicos. Arquivos atuais, inclusive não rastreados, registrados por SHA-256 em FASE_7F_C_PREFLIGHT.json. Não realizar commit, push, merge, release ou deploy.

## Evidência de implementação existente

- backend/app/execution.py: ActionRequest, Approval, ExecutionAuthorization, Job, WAITING_FOR_DEVICE, validação de revogação/expiração/kill switch, claim serializado por transação, lease e ledger sintético de reconciliação.
- backend/app/devices.py e backend/app/auth.py: devices antigos usam segredo bearer, não identidade Ed25519. Não tratar essa interface como cumprimento da 7F-C.
- backend/app/database.py: Store valida schema 4/5 e serializa mutações por UPDATE da linha schema_version. A inclusão da migration 0006 precisa preservar a compatibilidade dos testes existentes sem editar 0001–0005.
- backend/control_plane_app.py: distingue Owner Google, runtime e device legado. Novas rotas precisam de autenticação explícita, nunca fallback entre credenciais.
- web/src/pages/DevicesPage.tsx e componentes device-card/devices-panel: pontos de integração visual; preservar layout.

## Desenho a detalhar e implementar

1. Migration 0006 aditiva: identidade pública, enrollment, replay/counters, limites persistentes e estado de transporte. Snapshot da 0005 antes da edição de qualquer integrador.
2. Enrollment owner-bound com segredo de alta entropia, TTL curto, digest persistido, tentativa limitada e prova de posse Ed25519. Submissão da chave resulta apenas em PENDING_ENROLLMENT; ativação exige Owner e recent-auth. Código diferente do bootstrap Owner. Mostrar fingerprint antes da aprovação.
3. Protocolo Device v1 com schemas estritos e limites. Assinar método, caminho, identidade, versão, timestamp, sequência, nonce e hash dos bytes do payload em representação documentada e inequívoca. Verificar assinatura e consumir replay/counter atomicamente. Não implementar primitivas criptográficas próprias.
4. Tolerância proposta de relógio: 180 segundos, com replay protegido por sequência monotônica persistente e nonce. Timestamp não será único mecanismo de segurança. Heartbeat recebido no servidor determina last_seen; OFFLINE deriva da janela de heartbeat, sem revogação automática.
5. Usar Ed25519 da biblioteca cryptography já instalada. Private key protegida localmente por DPAPI do usuário Windows, ACL restrita e estado atômico de sequência; não enviar ao servidor nem registrar em relatórios. Falta da chave requer novo enrollment e nova aprovação. Clonagem não é absolutamente impedida.
6. Transporte outbound com HTTPS obrigatório fora de loopback, timeout, retry com backoff/jitter e parada cancelável. O agente não terá token Google, segredo OAuth, credencial administrativa ou acesso ao banco central. Identidade e counter sobrevivem a restart. Sem serviço Windows automático nesta etapa.
7. Integrar à fila canônica existente; não criar fila paralela com autoridade própria. Claim e validação de dispositivo/job/autorização devem ocorrer na mesma transação. Job LOCAL_DEVICE tem alvo explícito; ausência/offline nunca provoca fallback para cloud/outro PC. Resultado sintético vinculado a lease e idempotência, revalidando revogação/cancelamento/expiração/kill switch.
8. Impedir que endpoints bearer legados autentiquem uma identidade criptográfica nova. Preservação da baseline não pode criar caminho alternativo que contorne assinatura ou aprovação.
9. UI Devices real: adicionar, listar, confirmar fingerprint/capabilities, aprovar com recent-auth, renomear, revogar. Nenhuma ação de execução real.
10. Testes de matriz de segurança nos itens 70–71, incluindo concorrência real PostgreSQL, prova de posse, replay, restart, clock skew, revogação offline e fronteira Owner/device. Um job sintético pode comprovar o transporte sem efeito externo.

## Limites

Runtime Protocol v1 preservado. WEB_RESEARCH somente flag futura desabilitada. Sem Codex real, filesystem operacional, automação de navegador/desktop, integrações Google, pesquisa web, cloud adicional ou deploy. Manipulação local de arquivos necessária para identidade e testes não significa habilitar capability FILESYSTEM.

## Pendência de entrada

Receber a continuação do anexo a partir do item 72 antes de fechar o contrato de segurança, critérios de aceite e relatório final. Não presumir que os critérios da 7F-B substituem os ainda não recebidos da 7F-C.


## Atualização 2026-10-26

F.txt completo recebido (itens 0–99). Owner autorizou explicitamente a implementação em mensagem. A preparação acima é histórica; implementação e validações agora estão em andamento. Aceitação real exigirá intervenção Owner no item 91.
