// Aplica as migrations do schema `app` em produção (site.md §10: cada serviço migra só o seu schema).
//
//   docker compose run --rm --no-deps -T web node apps/web/scripts/migrate.mjs
//
// Usa o migrator do `drizzle-orm` (dependência de runtime), não o `drizzle-kit`, que é
// devDependency e não existe na imagem standalone. Lê os mesmos arquivos de
// drizzle/migrations e a mesma tabela de controle (app.__drizzle_migrations) que o
// `pnpm db:migrate` do desenvolvimento — os dois são intercambiáveis.
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { drizzle } from "drizzle-orm/postgres-js";
import { migrate } from "drizzle-orm/postgres-js/migrator";
import postgres from "postgres";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL ausente");
  process.exit(1);
}

const migrationsFolder = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "drizzle", "migrations");

// max: 1 — migração é sequencial; uma conexão evita lock concorrente entre réplicas.
const client = postgres(url, { max: 1, prepare: false });

try {
  await migrate(drizzle(client), {
    migrationsFolder,
    migrationsSchema: "app",
    migrationsTable: "__drizzle_migrations",
  });
  console.log("migrations do schema app aplicadas");
} catch (error) {
  console.error("falha ao migrar o schema app:", error);
  process.exitCode = 1;
} finally {
  await client.end();
}
