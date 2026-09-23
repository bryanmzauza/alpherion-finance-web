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
  // Auth (ADR-016). Em produção o segredo é obrigatório (ver `superRefine`).
  BETTER_AUTH_SECRET: z.string().min(32).optional(),
  BETTER_AUTH_URL: z.url().optional(),
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  // E-mail transacional (magic link). Em dev, o Mailpit do compose.
  SMTP_HOST: z.string().optional(),
  SMTP_PORT: z.coerce.number().int().positive().optional(),
  SMTP_USER: z.string().optional(),
  SMTP_PASSWORD: z.string().optional(),
  // Cifra das colunas financeiras (§7.4): AES-256-GCM, chave de 32 bytes em base64.
  APP_ENCRYPTION_KEY_V1: z.string().optional(),
  APP_ENCRYPTION_KEY_VERSION: z.coerce.number().int().positive().default(1),
}).superRefine((value, ctx) => {
  // Em produção, app sem segredo de sessão ou sem chave de cifra não sobe: melhor falhar
  // no boot do que aceitar login com segredo previsível ou gravar movimentação em claro.
  if (value.APP_ENV !== "prod") return;
  for (const name of ["BETTER_AUTH_SECRET", "APP_ENCRYPTION_KEY_V1"] as const) {
    if (!value[name]) ctx.addIssue({ code: "custom", path: [name], message: "obrigatória em produção" });
  }
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
