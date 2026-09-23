import { NextResponse } from "next/server";
import { z } from "zod";
import { auth, googleEnabled } from "@/lib/auth";
import { env } from "@/lib/env";
import { safeNext } from "@/lib/entrar";
import { rateLimit } from "@/lib/rate-limit";
import { clientIp, isSameOrigin } from "@/lib/request";

// POST /api/entrar/google — começa o login com Google (state + PKCE, pelo Better Auth).
//
// Formulário comum: a caixa de aceite é `required` no mesmo formulário do botão, e esta
// rota a confere de novo. A conta, se for nova, nasce no retorno do Google; o aceite é
// gravado nesse momento pelo hook de criação (`lib/signup-consent.ts`).

const bodySchema = z.object({ aceite: z.literal("on"), next: z.string().max(200).optional() });

export async function POST(request: Request): Promise<Response> {
  if (!googleEnabled) return NextResponse.json({ error: "Google não configurado" }, { status: 404 });
  if (!isSameOrigin(request.headers)) {
    return NextResponse.json({ error: "Origem inválida" }, { status: 403 });
  }
  const form = await request.formData().catch(() => null);
  const parsed = bodySchema.safeParse({ aceite: form?.get("aceite"), next: form?.get("next") ?? undefined });
  const next = safeNext(parsed.success ? parsed.data.next : null);
  if (!parsed.success) {
    return NextResponse.redirect(new URL(`/entrar?erro=dados&next=${encodeURIComponent(next)}`, env.APP_URL), 303);
  }

  const rl = await rateLimit("entrar-ip", clientIp(request.headers), 10, 600);
  if (!rl.ok) return NextResponse.redirect(new URL("/entrar?erro=limite", env.APP_URL), 303);

  // `asResponse`: a biblioteca devolve o JSON com a URL do Google **e** o cookie de state
  // do OAuth; repassamos o cookie num redirecionamento 303 para a URL do provedor.
  const response = await auth.api.signInSocial({
    body: {
      provider: "google",
      callbackURL: next,
      newUserCallbackURL: "/carteira/nova",
      errorCallbackURL: "/entrar?erro=google",
    },
    headers: request.headers,
    asResponse: true,
  });
  const data = (await response.json().catch(() => null)) as { url?: string } | null;
  if (!response.ok || !data?.url) {
    return NextResponse.redirect(new URL("/entrar?erro=google", env.APP_URL), 303);
  }

  const redirect = NextResponse.redirect(data.url, 303);
  for (const cookie of response.headers.getSetCookie()) {
    redirect.headers.append("set-cookie", cookie);
  }
  return redirect;
}
