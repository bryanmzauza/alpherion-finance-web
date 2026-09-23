import { and, eq, isNull } from "drizzle-orm";
import { consents } from "@/drizzle/schema";
import { db } from "@/lib/db";
import { sha256 } from "@/lib/hash";
import { LEGAL } from "@/lib/legal";

// Aceite de Termos + Privacidade no primeiro acesso ao app (site.md §2.2, §8.1; ADR-016).
//
// O magic link cria a conta só quando a pessoa clica no link, minutos depois de marcar a
// caixa no `/entrar`. Por isso o aceite é gravado **no momento em que ela marca a caixa**,
// pelo hash do e-mail (como a newsletter já faz), e ligado ao usuário quando a conta
// nasce — `linkSignupConsents`, chamado pelo hook de criação de usuário do Better Auth.
//
// No login com Google a conta nasce no retorno do provedor, sem passar pelo nosso
// formulário: a caixa é exigida na tela antes do botão, e o aceite é gravado no hook com o
// IP e o user agent da própria criação.

export const normalizeEmail = (email: string): string => email.trim().toLowerCase();

type RequestMeta = { ip: string | null; userAgent: string | null };

export async function recordSignupConsent(email: string, meta: RequestMeta): Promise<void> {
  const hash = sha256(normalizeEmail(email));
  await db.insert(consents).values([
    {
      subscriberEmailHash: hash,
      kind: "terms",
      documentVersion: LEGAL.termos.version,
      source: "app_signup",
      ip: meta.ip,
      userAgent: meta.userAgent,
    },
    {
      subscriberEmailHash: hash,
      kind: "privacy",
      documentVersion: LEGAL.privacidade.version,
      source: "app_signup",
      ip: meta.ip,
      userAgent: meta.userAgent,
    },
  ]);
}

/**
 * Liga o aceite gravado no `/entrar` à conta recém-criada. Se não houver aceite pendente
 * (conta criada pelo Google), grava o aceite agora, com os dados da própria requisição.
 */
export async function linkSignupConsents(userId: string, email: string, meta: RequestMeta): Promise<void> {
  const hash = sha256(normalizeEmail(email));
  const linked = await db
    .update(consents)
    .set({ userId })
    .where(and(eq(consents.subscriberEmailHash, hash), eq(consents.source, "app_signup"), isNull(consents.userId)))
    .returning({ id: consents.id });
  if (linked.length > 0) return;

  await db.insert(consents).values([
    { userId, kind: "terms", documentVersion: LEGAL.termos.version, source: "app_signup", ip: meta.ip, userAgent: meta.userAgent },
    { userId, kind: "privacy", documentVersion: LEGAL.privacidade.version, source: "app_signup", ip: meta.ip, userAgent: meta.userAgent },
  ]);
}
