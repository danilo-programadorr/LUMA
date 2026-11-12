# LUMA UI — demonstração local

Interface extraída, corrigida e validada sem backend. Todos os agentes, dispositivos, permissões, métricas e comandos são demonstrações locais.

## Executar

Requisitos: Node.js 22.12+ (validado com 24.18.0), pnpm 10.12.3.

```powershell
pnpm install --frozen-lockfile
pnpm dev
```

Acesso: http://127.0.0.1:8080. Não requer credenciais nem arquivo .env.

```powershell
pnpm typecheck
pnpm lint
pnpm build
pnpm preview
```

O build é de produção e sai em dist/. A aplicação usa React Router; hospedagem futura deverá redirecionar rotas da SPA para index.html.

## Escopo

React 19, Vite 7, TypeScript 5.9, Tailwind 3, shadcn/Radix, Framer Motion, Lucide. Dados demonstrativos em src/mocks/. Fontes Inter, Rajdhani e JetBrains Mono são carregadas do Google Fonts, com fallback de sistema. Analytics desativado; nenhum backend conectado.

Relatórios: AUDITORIA_INICIAL_UI.md e reports/. Screenshots: reports/ui-smoke/. Scripts de navegador em reports/ usam o Chromium e Playwright disponíveis nesta máquina; ajustar os caminhos para repetir em outra máquina.

Não integrar à LUMA oficial nem fazer push sem uma etapa posterior explicitamente autorizada.
