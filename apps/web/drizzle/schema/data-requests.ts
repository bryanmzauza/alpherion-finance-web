import { text, timestamp, uuid } from "drizzle-orm/pg-core";
import { app } from "./app";

// Atendimento aos direitos do titular (site.md §4.1; LGPD art. 18). Prazo interno: 15 dias.
export const dataRequestKind = app.enum("data_request_kind", ["access", "export", "delete", "correct", "portability"]);
export const dataRequestStatus = app.enum("data_request_status", ["open", "in_progress", "fulfilled", "rejected"]);

export const dataRequests = app.table("data_requests", {
  id: uuid("id").primaryKey().defaultRandom(),
  userId: uuid("user_id"),
  email: text("email").notNull(),
  kind: dataRequestKind("kind").notNull(),
  status: dataRequestStatus("status").notNull().default("open"),
  requestedAt: timestamp("requested_at", { withTimezone: true }).notNull().defaultNow(),
  fulfilledAt: timestamp("fulfilled_at", { withTimezone: true }),
  notes: text("notes"),
});
