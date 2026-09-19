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
# Variáveis só para o build passar pela validação de env; em runtime vêm do .env do compose.
ENV DATABASE_URL=postgres://build APP_ENV=prod API_SERVICE_TOKEN_WEB=build-placeholder-token-0000000000000000
RUN pnpm --filter web build

FROM node:22-slim AS runner
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./
COPY --from=build --chown=node:node /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=node:node /repo/apps/web/public ./apps/web/public
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
