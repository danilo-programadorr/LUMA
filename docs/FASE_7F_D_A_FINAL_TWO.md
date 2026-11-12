# Candidata final de duas chamadas — aguardando Owner

Autorizado agora: ajustes locais e testes sintéticos. Chamadas adicionais ainda não autorizadas. As6 chamadas originais estão encerradas e seu ledger não pode ser reaberto, alterado ou apagado. O novo perfil FINAL_TWO tem um ledger independente, limite fixo2 e uma tentativa por caso. Não usar este documento como autorização financeira.

A candidata pede futuras respostas em texto simples e conciso, com preferência por fontes primárias e uso exclusivo de documentação oficial quando solicitado. É uma direção ao provider, não garantia factual nem verificação de domínio por título. Resposta, citações, URLs e HTML Google recebidos não são reescritos, deduplicados ou removidos. Não há novo renderer Markdown ou dependência.

Contadores disponíveis do SDK: entrada, saída, thought, tool-use, total e cache; somente números não negativos. Campo ausente é UNKNOWN/null, não0. Aliases numéricos documentados são aceitos quando consistentes; conflito é rejeitado. Nenhum pensamento/summary, texto de resposta, URL, HTML ou mensagem livre de erro entra na persistência operacional. Total não é inferido pela soma de categorias potencialmente sobrepostas; billing real continua desconhecido.

Escopo proposto para autorização futura:

1. **public_scientific**, uma chamada Google Search: O que a NASA explica sobre as causas de um eclipse lunar? Responda brevemente com fonte. URL opcional deve ficar vazia.
2. **public_url_context**, uma chamada URL Context: Explique brevemente a compreensão de listas da página pública selecionada e cite essa página. URL única selecionada: https://docs.python.org/3/tutorial/datastructures.html

Modelo gemini-3.8-flash; máximo2000 tokens de saída por chamada, thinking low, sem summaries e sem retries pagos. Uma chamada Google Search pode executar mais de uma query. Franquia/billing não verificados; dois pedidos não são teto em dólares. Nenhuma API, conta, infraestrutura ou credencial nova. Perguntas e tool/URL são congelados; pedidos fora do plano ou repetição são rejeitados antes da chamada paga.

Após autorização explícita do Owner, usar o mesmo PowerShell com a chave existente e a mesma identidade de dispositivo, sem novo enrollment. Launcher preparado: scripts/run_research_final_acceptance.ps1. Sem -OwnerApprovedFinalTwo ele recusa execução. -Mode status apenas consulta o estado, sem chave ou reserva. O switch de aprovação só deve ser usado após o Owner aprovar este escopo. Ele habilita flags apenas no processo e restaura as anteriores ao encerrar.

As solicitações continuam sendo criadas pelo Owner na UI autenticada. Não há envio automático das duas perguntas pelo launcher. Enviar uma pergunta de cada vez, aguardar retorno e avaliar atribuição/navegação. Uma tentativa inconclusiva bloqueia qualquer outra até revisão; um erro interrompe a rodada; terminar as duas encerra o processo. Reiniciar não cria saldo novo. Não repetir a mesma pergunta para testar novamente.

Critério de fechamento real: ciência com evidência primária apropriada, URL Context com retrieval bem-sucedido da URL selecionada, citações válidas, sugestões Google intactas e navegação direta quando presentes, contadores numéricos preservados, nenhum conteúdo Google persistido, auditoria e secret scan. Falha/ambiguidade não é promovida a PASS. Sem fase7F-D-A2/7F-D-B, Codex real, commit, push ou deploy.


Atualização do Owner: autorizadas até3 chamadas adicionais em2026-10-29. Este roteiro de2 foi substituído; não usar seu switch antigo. Consulte docs/FASE_7F_D_A_FINAL_THREE.md e o novo precheck. Nenhuma chamada havia sido feita no perfil de2.
