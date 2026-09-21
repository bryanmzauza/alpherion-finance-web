import { NextResponse } from "next/server";
import { z } from "zod";
import { consents } from "@/drizzle/schema";
import { db } from "@/lib/db";
import { sha256 } from "@/lib/hash";
import { LEGAL } from "@/lib/legal";
import { ListmonkError, subscribe } from "@/lib/listmonk";
import { rateLimit } from "@/lib/rate-limit";
import { clientIp, isSameOrigin, userAgent } from "@/lib/request";

// POST /api/subscribe — inscrição na lista (site.md §2.1, §4.1, §8.1).
// zod → honeypot → rate limit 10/min/IP → Listmonk (double opt-in) → prova em `consents`.
// Resposta sempre igual para e-mail novo ou já cadastrado (sem enumeração).

const bodySchema = z.object({
  email: z.email().max(254).transform((e) => e.trim().toLowerCase()),
  consent: z.literal(true),
  website: z.literal("").optional(), // honeypot
});

const ok = () => NextResponse.json({ ok: true });

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request.headers)) {
    return NextResponse.json({ error: "Origem inválida" }, { status: 403 });
  }

  const raw: unknown = await request.json().catch(() => null);
  // Honeypot preenchido: bot. Responde sucesso e não faz nada.
  if (raw && typeof raw === "object" && "website" in raw && raw.website) return ok();

  const parsed = bodySchema.safeParse(raw);
  if (!parsed.success) {
    return NextResponse.json({ error: "Dados inválidos" }, { status: 400 });
  }

  const ip = clientIp(request.headers);
  const rl = await rateLimit("subscribe", ip, 10, 60);
  if (!rl.ok) {
    return NextResponse.json({ error: "Muitas tentativas" }, { status: 429, headers: { "Retry-After": "60" } });
  }

  try {
    await subscribe(parsed.data.email);
  } catch (err) {
    const status = err instanceof ListmonkError ? err.status : "?";
    console.error(`[subscribe] falha no Listmonk (status ${status})`);
    return NextResponse.json({ error: "Serviço indisponível" }, { status: 502 });
  }

  // Prova de consentimento (LGPD art. 8 §2). O e-mail fica só no Listmonk; aqui, o hash.
  await db.insert(consents).values({
    subscriberEmailHash: sha256(parsed.data.email),
    kind: "newsletter",
    documentVersion: LEGAL.privacidade.version,
    ip,
    userAgent: userAgent(request.headers),
    source: "landing",
  });

  return ok();
}
