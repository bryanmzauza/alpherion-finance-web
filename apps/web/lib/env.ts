import { z } from "zod";
import { loadRootEnv } from "@/lib/root-env";

loadRootEnv();

// Variáveis que o web precisa (infra/env/.env.example). Validadas uma vez no boot
// (instrumentation.ts). Nunca importar este módulo em código de cliente.
const isTest = process.env.NODE_ENV === "test";

const schema = z.object({
  APP_ENV: z.enum(["dev", "prod"]).default("dev"),
  SITE_URL: z.url().default("http://localhost:3000"),
  APP_URL: z.url().default("http://localhost:3000"),
  API_URL: z.url().default("http://localhost:8000"),
  DATABASE_URL: isTest ? z.string().default("postgres://test") : z.string().min(1),
  API_SERVICE_TOKEN_WEB: isTest ? z.string().default("test-token") : z.string().min(32),
  REDIS_URL: z.string().optional(),
  // Lista de e-mail (Listmonk). Opcionais: sem eles, /api/subscribe responde 502.
  LISTMONK_URL: z.url().optional(),
  LISTMONK_API_USER: z.string().optional(),
  LISTMONK_API_TOKEN: z.string().optional(),
  LISTMONK_LIST_ID: z.coerce.number().int().positive().optional(),
  LISTMONK_OPTIN_TEMPLATE_ID: z.coerce.number().int().positive().optional(),
  EMAIL_FROM_TRANSACTIONAL: z.email().optional(),
  // Umami (analytics sem cookie). Sem eles, o script não é injetado.
  UMAMI_WEBSITE_ID: z.string().optional(),
  UMAMI_SCRIPT_URL: z.url().optional(),
});

export type Env = z.infer<typeof schema>;

export function parseEnv(source: Record<string, string | undefined> = process.env): Env {
  const result = schema.safeParse(source);
  if (!result.success) {
    const issues = result.error.issues.map((i) => `  - ${i.path.join(".")}: ${i.message}`).join("\n");
    throw new Error(`Variáveis de ambiente inválidas (veja infra/env/.env.example):\n${issues}`);
  }
  return result.data;
}

export const env: Env = parseEnv();
