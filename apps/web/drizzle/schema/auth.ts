import { boolean, index, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";
import { app } from "./app";

// Identidade (site.md §4.1, ADR-016). As tabelas seguem o schema do Better Auth — as
// chaves JS são os nomes de campo que a biblioteca usa (`emailVerified`, `expiresAt`…) e
// as colunas no banco ficam em snake_case. Os nomes das tabelas são os do §4.1; o mapeamento
// modelo → tabela está em `lib/auth.ts`.
//
// Ids são UUID gerados **pelo banco** (`generateId: "uuid"` no Better Auth quer dizer isso:
// o adapter omite o id e espera o default da coluna). O mesmo tipo de `consents.user_id`.

const timestamps = {
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
};

export const users = app.table(
  "users",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    // Nome é opcional (minimização, §4.1): o Better Auth exige a coluna, e ela fica vazia
    // quando a pessoa não informa. Não copiamos nome nem foto do Google.
    name: text("name").notNull().default(""),
    email: text("email").notNull(),
    emailVerified: boolean("email_verified").notNull().default(false),
    image: text("image"),
    locale: text("locale").notNull().default("pt-BR"),
    plan: text("plan").notNull().default("free"),
    // Carência de 7 dias antes da exclusão definitiva (§4.1).
    deleteRequestedAt: timestamp("delete_requested_at", { withTimezone: true }),
    deletedAt: timestamp("deleted_at", { withTimezone: true }),
    ...timestamps,
  },
  // E-mail único sem diferenciar caixa: `Fulano@x.com` e `fulano@x.com` são a mesma conta.
  (t) => [uniqueIndex("users_email_lower_idx").on(sql`lower(${t.email})`)],
);

export const sessions = app.table(
  "sessions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    token: text("token").notNull().unique(),
    ipAddress: text("ip_address"),
    userAgent: text("user_agent"),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    ...timestamps,
  },
  (t) => [index("sessions_user_id_idx").on(t.userId)],
);

export const accounts = app.table(
  "accounts",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    accountId: text("account_id").notNull(),
    providerId: text("provider_id").notNull(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    // Tokens do provedor OAuth: cifrados pelo Better Auth (`encryptOAuthTokens`).
    accessToken: text("access_token"),
    refreshToken: text("refresh_token"),
    idToken: text("id_token"),
    accessTokenExpiresAt: timestamp("access_token_expires_at", { withTimezone: true }),
    refreshTokenExpiresAt: timestamp("refresh_token_expires_at", { withTimezone: true }),
    scope: text("scope"),
    // Sem senha no v1 (ADR-007); a coluna existe porque é do schema da biblioteca.
    password: text("password"),
    ...timestamps,
  },
  (t) => [index("accounts_user_id_idx").on(t.userId)],
);

// Tokens de magic link: guardados em hash (`storeToken: "hashed"`), uso único, 15 min.
export const verificationTokens = app.table(
  "verification_tokens",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    identifier: text("identifier").notNull(),
    value: text("value").notNull(),
    expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
    ...timestamps,
  },
  (t) => [index("verification_tokens_identifier_idx").on(t.identifier)],
);
