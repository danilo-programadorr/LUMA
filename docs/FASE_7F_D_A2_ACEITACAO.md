# Biblioteca privada — aceitação local 7F-D-A2

Estado em 30/10/2026: implementação e validação local prontas; aceitação pelo Owner pendente. Backend e Web candidatos, sem promoção stable. Não iniciar outra fase.

## Primeiro teste sem dados privados

1. Abra http://localhost:5173/knowledge no navegador usado para a LUMA e entre com sua conta Google, se necessário.
2. Em **Computador da biblioteca**, selecione o PC existente. Clique em **Autorizar biblioteca neste PC**. Se a permissão exigir autenticação recente, clique **Confirmar identidade**, conclua o Google e tente autorizar novamente. Não é preciso novo enrollment nem código de vínculo do proprietário.
3. No PowerShell, importe o exemplo preparado e mantenha o agente em execução:

```powershell
Set-Location 'D:\projetos\luma'
.\scripts\run_private_library.ps1 -Mode import -File '.\examples\private-library\guia-sintetico.txt'
.\scripts\run_private_library.ps1 -Mode run
```

4. Em Conhecimento, clique **Atualizar fontes**. Escolha o mesmo PC, confira o documento ativo e consulte: **Quem revisa o inventário e quando?** A busca retorna trechos originais e linhas; não gera uma interpretação por modelo. Espere encontrar equipe Azul e segunda-feira nas referências do exemplo.
5. Confira **Biblioteca online**, as linhas citadas e o título. Arquivar uma fonte deve impedi-la de participar de novas consultas; isso preserva original e histórico.
6. Para testar a interrupção, clique **Suspender biblioteca neste PC**. Os trechos devem desaparecer e o agente deve encerrar com `LIBRARY_CAPABILITY_REQUIRED`. Autorizar novamente exige decisão explícita do Owner.

Não repita uma importação se ela falhar por permissão: primeiro confira a autorização atual. O mesmo arquivo/projeto/dispositivo não deve criar duplicata. Um conteúdo alterado gera nova fonte. Não execute novo enrollment.

## Seus documentos

Depois do exemplo, use o mesmo comando `-Mode import -File` com um caminho de arquivo escolhido por você. Compatíveis: PDF com texto, TXT UTF-8 e Markdown UTF-8, até 8 MiB. Apenas o arquivo indicado é lido; não há varredura de pastas, download por URL, OCR, PDF com senha, DOCX ou EPUB nesta versão. Não cole chaves ou informações privadas no chat para testar.

Os originais e o índice ficam cifrados no runtime local. O cadastro central recebe título, hash, contagens e a pergunta original da consulta. Os trechos passam temporariamente pelo Control Plane para exibição autenticada, sem persistência no banco ou browser storage. Não são enviados ao Gemini, à pesquisa web ou a embeddings. Arquivar/suspender não apaga os arquivos.

## Evidência técnica disponível

1.043 casos únicos PASS: 852 backend, 81 PostgreSQL real isolado, 84 frontend e 26 browser. Baseline anterior de956 preservada. Reexecuções não somadas. Tipos/lint/build PASS; permanece aviso de bundle frontend grande. Capturas sintéticas em reports/7fda2-ui; não comprovam interação real do Owner.

PostgreSQL Owner real migrado de7 para8 após backup privado, com `pg_restore --list` PASS. Nenhum ensaio completo de restore foi realizado. Portas locais:55432 banco,8770 backend,5173 Web. Nenhuma capacidade foi concedida automaticamente; banco da biblioteca está vazio. A identidade assinada existente passou até o gate esperado `LIBRARY_CAPABILITY_REQUIRED`.

Relatório: reports/FASE_7F_D_A2_RELATORIO.json. Auditoria: reports/FASE_7F_D_A2_AUDIT.json. Testes: reports/FASE_7F_D_A2_TEST_SUMMARY.json. Secret scan final: reports/FASE_7F_D_A2_SECRET_SCAN.json. Sem chamadas pagas, APIs novas, cloud, commit, push, deploy, voz ou Codex real. A chamada pública restante da fase anterior foi preservada e não é orçamento da biblioteca.
