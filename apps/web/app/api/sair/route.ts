import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { env } from "@/lib/env";
import { isSameOrigin } from "@/lib/request";

// POST /api/sair — encerra a sessão (formulário do cabeçalho do app; sem JavaScript).
// O `logout` vai para o `audit_log` pelo hook de `/sign-out` em `lib/auth.ts`.
export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request.headers)) {
    return NextResponse.json({ error: "Origem inválida" }, { status: 403 });
  }
  const response = await auth.api.signOut({ headers: request.headers, asResponse: true });
  const redirect = NextResponse.redirect(new URL("/entrar", env.APP_URL), 303);
  for (const cookie of response.headers.getSetCookie()) {
    redirect.headers.append("set-cookie", cookie);
  }
  return redirect;
}
