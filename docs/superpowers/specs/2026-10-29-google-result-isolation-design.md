# Proposta curta — resultado Google em aba isolada

Status: escolha técnica de implementação pelo Codex dentro do mecanismo de isolamento equivalente já autorizado pelo Owner (correção do gate, seção2), agora solicitada como correção do erro. A aba isolada é escolha do implementador, não preferência atribuída ao Owner. A correção independente da comunicação FAILED já foi escrita e passou nos testes direcionados.

Problema observado: o HTML retornado na primeira chamada não atende à exigência local de que todos os links usem target=_blank. Não foi armazenado nem será reconstruído. A resposta Google demorou6,783s; a tela terminou em timeout porque o backend também recusou a entrega do erro FAILED sem artefato. Essa condição foi corrigida separadamente.

Abordagens consideradas:
- Manter exclusivamente o iframe atual: conserva a segurança, mas continua incompatível com links que navegam no próprio contexto.
- Alterar links, targets ou injetar regras de navegação nas sugestões: descartado, pois muda o comportamento do HTML e cria ambiguidade com as condições do Owner.
- Proposta recomendada: exibir resposta, citações e HTML original juntos em uma aba temporária isolada. A página da LUMA permanece aberta. Os links seguem diretamente ao destino fornecido pelo Google, inclusive quando não possuem target=_blank.

Desenho: entrega apenas do runtime Google autenticado; autorização Owner existente emite acesso aleatório de uso único à apresentação temporária em RAM. Nenhum HTML/texto/URL de Google em banco, reports, histórico ou storage. Documento próprio fora do DOM da LUMA; CSP restritiva, origem opaca/sandbox, sem acesso ao aplicativo ou credenciais, sem scripts fornecidos pelo Google, sem formulários, sem tracking ou reescrita de links. Apenas código estático confiável e identificado por hash, se necessário para expirar/limpar a apresentação; nunca liberar execução arbitrária. Sem iframe da página de destino Google. Headers no-store e referrer-policy no-referrer. Expiração/refresh mostram resultado não retido e não fazem nova pesquisa.

Aceitação local necessária: HTML intacto; navegação real de mocks com target ausente/_self/_blank; scripts e acesso a storage/DOM da LUMA bloqueados; expiração/refresh sem reutilização; nenhuma persistência; sem tracking; usuário vê resposta e sugestões associadas. Caso algum teste ou requisito permaneça ambíguo, manter bloqueado.

Custo/escopo: nenhuma chamada real para desenvolver ou testar. Contador preservado em1 chamada/2 queries; limite original6, portanto5 tentativas restantes, sem reiniciar a contagem. A pesquisa real só pode retomar após validação técnica completa, conforme retomada já autorizada na seção19 da correção do Owner. Sem cloud/API/credencial nova, commit, push, deploy, Codex real ou próxima fase.

Referências: https://ai.google.dev/gemini-api/terms ; https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/sandbox . A proposta técnica não constitui dispensa de requisitos do provider.
