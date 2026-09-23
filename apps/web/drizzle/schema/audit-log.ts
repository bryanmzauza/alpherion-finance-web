import { bigserial, index, jsonb, text, timestamp, uuid } from "drizzle-orm/pg-core";
import { app } from "./app";

// Trilha de auditoria (site.md §4.4). **Append-only**: a migration revoga UPDATE e DELETE
// e instala um trigger que recusa as duas operações — revogar sozinho não basta, porque o
// dono do schema pode se devolver o privilégio.
//
// Sem PII: nada de e-mail, posição ou conteúdo de arquivo. `user_id` é o id interno, e o
// IP fica para investigação de incidente (§7.7).
export const auditAction = app.enum("audit_action", [
  "login",
  "logout",
  "import",
  "portfolio_create",
  "transaction_delete",
  "export",
  "delete_request",
]);

export const auditLog = app.table(
  "audit_log",
  {
    id: bigserial("id", { mode: "number" }).primaryKey(),
    userId: uuid("user_id"),
    action: auditAction("action").notNull(),
    ip: text("ip"),
    userAgent: text("user_agent"),
    // Contexto sem dado pessoal: método de login, id do lote importado, contagens.
    details: jsonb("details").$type<Record<string, string | number | boolean | null>>(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("audit_log_user_id_created_idx").on(t.userId, t.createdAt)],
);
