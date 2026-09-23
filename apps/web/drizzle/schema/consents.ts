import { index, inet, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { app } from "./app";
import { users } from "./auth";

// Prova de consentimento (site.md §4.1; LGPD art. 8 §2). Sem e-mail em claro: a lista
// vive no Listmonk; aqui fica só o hash do e-mail para ligar prova ↔ assinante.
export const consentKind = app.enum("consent_kind", ["terms", "privacy", "newsletter"]);
export const consentSource = app.enum("consent_source", ["landing", "app_signup", "app_settings"]);

export const consents = app.table("consents", {
  id: uuid("id").primaryKey().defaultRandom(),
  // Aceite no /entrar é gravado antes de a conta existir (pelo hash do e-mail) e ligado ao
  // usuário quando ele é criado — ver `lib/auth.ts`.
  userId: uuid("user_id").references(() => users.id, { onDelete: "set null" }),
  subscriberEmailHash: text("subscriber_email_hash"),
  kind: consentKind("kind").notNull(),
  documentVersion: text("document_version").notNull(),
  acceptedAt: timestamp("accepted_at", { withTimezone: true }).notNull().defaultNow(),
  ip: inet("ip"),
  userAgent: text("user_agent"),
  source: consentSource("source").notNull(),
  withdrawnAt: timestamp("withdrawn_at", { withTimezone: true }),
}, (t) => [index("consents_subscriber_email_hash_idx").on(t.subscriberEmailHash), index("consents_user_id_idx").on(t.userId)]);
