import { NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/lib/auth";
import { env } from "@/lib/env";
import { createPortfolio } from "@/lib/portfolio/repo";
import { clientIp, isSameOrigin, userAgent } from "@/lib/request";

// POST /api/portfolio — cria a carteira (passo 1 de `/carteira/nova`). Formulário HTML;
// uma carteira por pessoa no v1: se já existe, segue para o passo 2 sem criar outra.

const schema = z.object({ nome: z.string().trim().min(1).max(60) });

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request.headers)) return NextResponse.json({ error: "Origem inválida" }, { status: 403 });
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) return NextResponse.redirect(new URL("/entrar?next=/carteira/nova", env.APP_URL), 303);

  const form = await request.formData().catch(() => null);
  const parsed = schema.safeParse({ nome: form?.get("nome") });
  if (!parsed.success) return NextResponse.redirect(new URL("/carteira/nova?erro=nome", env.APP_URL), 303);

  await createPortfolio(session.user.id, parsed.data.nome, {
    ip: clientIp(request.headers),
    userAgent: userAgent(request.headers),
  });
  return NextResponse.redirect(new URL("/carteira/nova?passo=2", env.APP_URL), 303);
}
