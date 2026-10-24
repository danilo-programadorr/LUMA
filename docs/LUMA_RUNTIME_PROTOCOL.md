# Protocolo runtime v1

Schemas canônicos: contracts/RUNTIME_PROTOCOL_V1.json.
Implementação: backend/remote_protocol.py. Todos os objetos são Pydantic strict,
frozen, extra=forbid e protocol_version literal "1". JSON é o formato de transporte.

| Contrato | Conteúdo |
| --- | --- |
| RemoteTaskEnvelope | task/project/session/device/runtime/correlation, created_at/expires_at, tipo, mensagem, contexto limitado, idempotency key, registry version e scope |
| RuntimeResultEnvelope | answer/proposal/error/model-result, runtime_status, IDs vinculados, citações limitadas e resumo de agentes |
| RuntimeProposalEnvelope | tool/operation/project/workspace/parameters/resource/destination, target local e risk hint |
| RuntimeHeartbeat | runtime/device, registry version e status; sem autoridade |
| RuntimeErrorEnvelope | IDs e código seguro; sem exceção ou stack trace |

Limites: frame 262144 bytes UTF-8; mensagem 2000 caracteres; resposta 4000;
contexto até 4 mensagens, 2000 caracteres cada e 8000 bytes combinados;
proposal até 16 parâmetros string, 2000 caracteres por valor e 8192 bytes;
até 5 citações de 200 caracteres; até 6 eventos resumidos de agentes.
Knowledge do MODEL_GENERATION integrado também está contido pelo limite total.
Tasks têm TTL máximo 600 segundos; o gateway emite 300 segundos.
Datas exigem timezone. Runtime rejeita task expirada antes de trabalhar; o
Control Plane revalida a validade ao receber resultado. Runtime não pode estendê-la.

Campos de aprovação/Owner/authorization/grant/unlock não pertencem ao protocolo.
Campos extras são rejeitados, inclusive owner_id e effective risk.
Parameters passam por validação estrutural e pela operação canônica.
Runtime status não é task status: somente o gateway define o estado persistido.
risk_hint não altera o risco obtido da definição canônica da ferramenta.

Snapshot de registry é hash de tools e agents atuais. Mudança entre emissão e
resultado rejeita o retorno com RUNTIME_POLICY_STALE. Grants são revalidados ao
vivo independentemente do hash. Não há fallback de projeto.

Erros seguros distinguem RUNTIME_UNAVAILABLE, RUNTIME_PROTOCOL_ERROR,
MODEL_ERROR, KNOWLEDGE_UNAVAILABLE, POLICY_DENIED e TECHNICAL_FAILURE.
Esclarecimento é resultado de domínio. Erro de policy não é convertido em sucesso
nem em aprovação. Texto de exceção de provider não cruza a fronteira.

Trace contém agente, nó, tipo de decisão, duração limitada e status. Não possui
campo de raciocínio privado/CoT. Answer e reason_summary são saídas limitadas e
não confiáveis, nunca instruções para executar.
O handler local conserva validação de referências Knowledge, recusa alegações
de execução e bloqueia retorno de credenciais conhecidas.

LocalRuntimeTransport serializa envelopes; FutureRemoteRuntimeTransport falha
fechado com RUNTIME_UNAVAILABLE. HTTPS, assinatura de dispositivo e polling
não foram implementados. Testes de snapshot detectam alterações de schema;
mudanças incompatíveis requerem decisão explícita de versionamento.
