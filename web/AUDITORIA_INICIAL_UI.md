# Auditoria inicial — LUMA UI

Estado original registrado em reports/original-files.json (SHA-256). Pasta sem Git, sem node_modules e sem lockfile. Nenhuma alteração na LUMA oficial.

Stack declarada: React 19.1, TypeScript 5.9, Vite 7.1, Tailwind 3.4, shadcn/Radix, Lucide 0.542, Framer Motion 12, React Router 7, React Context e TanStack Query 5. Sem Next.js. pnpm escolhido pelos scripts e README existentes, pois nenhum lockfile foi extraído.

Problemas confirmados inicialmente (12 grupos; contagem final após verificações):
1. Manifesto packege.json incorreto: instalação/scripts bloqueados.
2. Ausência de lockfile: resolução original não reproduzível.
3. Diretório e dois arquivos error-boundary com nomes incorretos.
4. DevicesPage e ProjectsPage com nomes incorretos.
5. luma-data e timeline-panel com nomes incorretos.
6. carousel e resizable com nomes incorretos.
7. Build usa atribuição POSIX incompatível com Windows e modo development.
8. Check executa tsc na configuração raiz sem verificar projetos referenciados.
9. Servidor configurado para todas as interfaces (::).
10. Analytics Enter com bootstrap e endpoint externos.
11. Plugin de build Enter acoplado à plataforma; plugin React disponível mas não utilizado diretamente.
12. ESLint exclui todos os componentes shadcn; validação incompleta.

Categorias: B/C/D/F/G/J/K/L/Q/R/S. Assets, hooks, animações e responsividade ainda precisam de verificação executada. Baseline build: ENOENT package.json (log completo em baseline-build.log). Install/lint/typecheck bloqueados pelo mesmo manifesto ausente. Sem formatter configurado.

Estratégia: restaurar nomes esperados sem duplicar componentes; preservar código visual; usar plugin React padrão e scripts portáveis; desativar telemetria e remover dependências de backend somente após confirmar ausência de uso; instalar com pnpm e gerar um único lockfile; executar TypeScript, lint, build e navegador com matriz desktop/mobile. Registrar separadamente limitações comprovadas.
