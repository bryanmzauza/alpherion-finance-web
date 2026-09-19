import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { env } from "@/lib/env";
import * as schema from "@/drizzle/schema";

// Conexão do web com o Postgres: usuário `web`, schema `app` (site.md §7.6).
// Só código de servidor importa este módulo.
const client = postgres(env.DATABASE_URL, {
  max: 10,
  prepare: false,
});

export const db = drizzle(client, { schema });
export type Db = typeof db;
