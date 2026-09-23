import { auditLog } from "@/drizzle/schema";
import { db } from "@/lib/db";

// Registro na trilha de auditoria (site.md §4.4). Append-only no banco.
//
// Falha ao auditar não derruba a ação do usuário (um login não pode falhar porque a
// trilha está lenta), mas vai para o log de erro — auditoria que some em silêncio não
// é auditoria.

type AuditAction = (typeof auditLog.action.enumValues)[number];

export async function audit(
  action: AuditAction,
  entry: {
    userId: string | null;
    ip?: string | null;
    userAgent?: string | null;
    details?: Record<string, string | number | boolean | null>;
  },
): Promise<void> {
  try {
    await db.insert(auditLog).values({
      action,
      userId: entry.userId,
      ip: entry.ip ?? null,
      userAgent: entry.userAgent?.slice(0, 512) ?? null,
      details: entry.details ?? null,
    });
  } catch (error) {
    console.error(`[audit] falha ao registrar ${action}:`, (error as Error).message);
  }
}
