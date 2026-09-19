import { existsSync } from "node:fs";
import path from "node:path";
import { loadEnvConfig } from "@next/env";

// O `.env` fica na raiz do monorepo, não em apps/web. Sobe a árvore até achar o
// workspace e carrega de lá (sem sobrescrever o que já está em process.env).
// Em container (standalone) não há workspace: tudo vem do ambiente. Em `test`, não carrega.
export function loadRootEnv(): void {
  if (process.env.NODE_ENV === "test") return;
  let dir = process.cwd();
  for (let i = 0; i < 4; i += 1) {
    if (existsSync(path.join(dir, "pnpm-workspace.yaml"))) {
      loadEnvConfig(dir, process.env.NODE_ENV !== "production");
      return;
    }
    dir = path.dirname(dir);
  }
}
