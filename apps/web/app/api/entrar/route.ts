import { sql } from "drizzle-orm";
import { NextResponse } from "next/server";
import { users } from "@/drizzle/schema";
import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { env } from "@/lib/env";
import { entrarSchema, safeNext } from "@/lib/entrar";
import { sha256 } from "@/lib/hash";
import { rateLimit } from "@/lib/rate-limit";
import { clientIp, isSameOrigin, userAgent } from "@/lib/request";
import { recordSignupConsent } from "@/lib/signup-consent";

// POST /api/entrar — pede o magic link (site.md §2.2, §7.4).
//
// É um formulário HTML comum (funciona sem JavaScript): responde com redirecionamento
// 303 para `/entrar/verificar` ou de volta ao `/entrar` com o código do erro.
//
// A resposta é a mesma para e-mail com ou sem conta — não dá para descobrir quem é
// cliente testando e-mails. O aceite de Termos + Privacidade é gravado aqui só quando a
// conta ainda não existe (é o aceite do cadastro); ele é ligado ao usuário quando o link
// é usado.

const back = (code: string, next?: string) => {
  const url = new URL("/entrar", env.APP_URL);
  url.searchParams.set("erro", code);
  if (next) url.searchParams.set("next", next);
  return NextResponse.redirect(url, 303);
};

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request.headers)) {
    return NextResponse.json({ error: "Origem inválida" }, { status: 403 });
  }

  const form = await request.formData().catch(() => null);
  const parsed = entrarSchema.safeParse({
    email: form?.get("email"),
    aceite: form?.get("aceite"),
    next: form?.get("next") ?? undefined,
  });
  const next = safeNext(parsed.success ? parsed.data.next : (form?.get("next") as string | null));
  if (!parsed.success) return back("dados", next);

  const { email } = parsed.data;
  const ip = clientIp(request.headers);
  const [porIp, porEmail] = await Promise.all([
    rateLimit("entrar-ip", ip, 10, 600),
    rateLimit("entrar-email", sha256(email), 3, 600),
  ]);
  if (!porIp.ok || !porEmail.ok) return back("limite", next);

  const existing = await db
    .select({ id: users.id })
    .from(users)
    .where(sql`lower(${users.email}) = ${email}`)
    .limit(1);
  if (existing.length === 0) {
    await recordSignupConsent(email, { ip, userAgent: userAgent(request.headers) });
  }

  try {
    await auth.api.signInMagicLink({
      body: {
        email,
        callbackURL: next,
        newUserCallbackURL: "/carteira/nova",
        errorCallbackURL: "/entrar?erro=link",
      },
      headers: request.headers,
    });
  } catch (error) {
    console.error("[entrar] falha ao enviar o magic link:", (error as Error).message);
    return back("envio", next);
  }

  return NextResponse.redirect(new URL("/entrar/verificar", env.APP_URL), 303);
}
