# Contexto de build: a RAIZ do monorepo (precisa do lockfile e do workspace).
#   docker build -f apps/web/Dockerfile -t alpherion-web .
# Saída standalone do Next (next.config.ts: output "standalone"), usuário não-root.

FROM node:22-slim AS base
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable
WORKDIR /repo

FROM base AS deps
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

FROM deps AS build
COPY apps/web apps/web
ENV NEXT_TELEMETRY_DISABLED=1
# SITE_URL entra no build: metadataBase, canônicas, OG e sitemap são resolvidos contra ela.
ARG SITE_URL=https://alpherion.com.br
ENV SITE_URL=$SITE_URL
# Variáveis só para o build passar pela validação de env; em runtime vêm do .env do compose.
ENV DATABASE_URL=postgres://build APP_ENV=prod API_SERVICE_TOKEN_WEB=build-placeholder-token-0000000000000000
RUN pnpm --filter web build && pnpm --filter web build:migrator

FROM node:22-slim AS runner
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./
COPY --from=build --chown=node:node /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=node:node /repo/apps/web/public ./apps/web/public
# Migrations do schema `app` (site.md §10). `dist/migrate.mjs` é o `scripts/migrate.mjs`
# empacotado pelo esbuild com drizzle-orm e postgres embutidos: o standalone do Next não
# expõe node_modules (as deps do servidor vão para dentro do bundle) e drizzle-kit é devDependency.
COPY --from=build --chown=node:node /repo/apps/web/drizzle/migrations ./apps/web/drizzle/migrations
COPY --from=build --chown=node:node /repo/apps/web/dist/migrate.mjs ./apps/web/scripts/migrate.mjs
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
