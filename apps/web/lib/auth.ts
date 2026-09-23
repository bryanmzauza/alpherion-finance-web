import { betterAuth } from "better-auth";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { createAuthMiddleware, getSessionFromCtx } from "better-auth/api";
import { nextCookies } from "better-auth/next-js";
import { magicLink } from "better-auth/plugins";
import { SITE_NAME } from "@/content/site";
import { accounts, sessions, users, verificationTokens } from "@/drizzle/schema";
import { audit } from "@/lib/audit";
import { db } from "@/lib/db";
import { env } from "@/lib/env";
import { sendMagicLinkEmail } from "@/lib/mailer";
import { clientIp } from "@/lib/request";
import { linkSignupConsents } from "@/lib/signup-consent";

// Autenticação do app (site.md §7.4, ADR-016). Só código de servidor importa este módulo.
//
// O que cada opção garante:
// - magic link de **uso único** (a biblioteca consome o token na primeira verificação),
//   **15 minutos**, guardado em **hash** no banco;
// - Google com PKCE (padrão do provedor na biblioteca), sem copiar nome nem foto
//   (minimização, §4.1), com os tokens do provedor cifrados no banco;
// - sessão no banco (revogável em `/conta`), cookie `HttpOnly`, `SameSite=Lax`, `Secure`
//   em produção, **30 dias deslizantes** (renovada a cada dia de uso);
// - sem cache de sessão em cookie: o app usa um cookie só, o de sessão (§8.5).

const THIRTY_DAYS = 60 * 60 * 24 * 30;
const ONE_DAY = 60 * 60 * 24;
const isProd = env.APP_ENV === "prod";

const google =
  env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET
    ? {
        google: {
          clientId: env.GOOGLE_CLIENT_ID,
          clientSecret: env.GOOGLE_CLIENT_SECRET,
          // Só o e-mail interessa; nome e foto do Google não entram no nosso banco.
          mapProfileToUser: () => ({ name: "", image: undefined }),
        },
      }
    : undefined;

/** O botão "Entrar com Google" só aparece quando as credenciais existem. */
export const googleEnabled = google !== undefined;

function requestMeta(headers: Headers | undefined) {
  if (!headers) return { ip: null, userAgent: null };
  return { ip: clientIp(headers), userAgent: headers.get("user-agent")?.slice(0, 512) ?? null };
}

export const auth = betterAuth({
  appName: SITE_NAME,
  baseURL: env.BETTER_AUTH_URL ?? env.APP_URL,
  secret: env.BETTER_AUTH_SECRET,
  trustedOrigins: [env.APP_URL, env.SITE_URL],
  database: drizzleAdapter(db, {
    provider: "pg",
    schema: { users, sessions, accounts, verification_tokens: verificationTokens },
  }),
  user: {
    modelName: "users",
    additionalFields: {
      locale: { type: "string", required: false, input: false, defaultValue: "pt-BR" },
      plan: { type: "string", required: false, input: false, defaultValue: "free" },
    },
  },
  session: {
    modelName: "sessions",
    expiresIn: THIRTY_DAYS,
    updateAge: ONE_DAY,
    cookieCache: { enabled: false },
  },
  account: {
    modelName: "accounts",
    encryptOAuthTokens: true,
    // Mesmo e-mail pelo magic link e pelo Google é a mesma conta.
    accountLinking: { enabled: true, trustedProviders: ["google"] },
  },
  verification: { modelName: "verification_tokens" },
  emailAndPassword: { enabled: false },
  ...(google ? { socialProviders: google } : {}),
  advanced: {
    database: { generateId: "uuid" },
    useSecureCookies: isProd,
    defaultCookieAttributes: { httpOnly: true, sameSite: "lax", secure: isProd },
    // Atrás da Cloudflare + nginx (§7.2): o IP real vem destes cabeçalhos.
    ipAddress: { ipAddressHeaders: ["cf-connecting-ip", "x-real-ip"] },
  },
  rateLimit: { enabled: true, window: 60, max: 30 },
  plugins: [
    magicLink({
      expiresIn: 15 * 60,
      storeToken: "hashed",
      sendMagicLink: async ({ email, url }) => {
        await sendMagicLinkEmail(email, url);
      },
    }),
    // Tem de ser o último plugin: é ele que grava o cookie nas server actions.
    nextCookies(),
  ],
  databaseHooks: {
    user: {
      create: {
        after: async (user, ctx) => {
          await linkSignupConsents(user.id, user.email, requestMeta(ctx?.request?.headers ?? ctx?.headers));
        },
      },
    },
    session: {
      create: {
        after: async (session, ctx) => {
          const path = ctx?.path ?? "";
          await audit("login", {
            userId: session.userId,
            ...requestMeta(ctx?.request?.headers ?? ctx?.headers),
            details: { method: path.includes("magic-link") ? "magic_link" : path.includes("callback") ? "google" : "outro" },
          });
        },
      },
    },
  },
  hooks: {
    // Logout: a sessão ainda existe no `before`, então é aqui que se sabe quem saiu.
    before: createAuthMiddleware(async (ctx) => {
      if (ctx.path !== "/sign-out") return;
      const current = await getSessionFromCtx(ctx);
      if (current) {
        await audit("logout", { userId: current.user.id, ...requestMeta(ctx.request?.headers ?? ctx.headers) });
      }
    }),
  },
});

export type AuthSession = typeof auth.$Infer.Session;
