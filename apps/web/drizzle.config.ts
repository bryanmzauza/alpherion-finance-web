import { defineConfig } from "drizzle-kit";
import { loadRootEnv } from "./lib/root-env";

loadRootEnv();

// Só o schema `app` pertence ao web. O `market` é da API (SQLAlchemy/Alembic).
export default defineConfig({
  dialect: "postgresql",
  schema: "./drizzle/schema/index.ts",
  out: "./drizzle/migrations",
  schemaFilter: ["app"],
  dbCredentials: {
    url: process.env.DATABASE_URL ?? "",
  },
  strict: true,
  verbose: true,
});
