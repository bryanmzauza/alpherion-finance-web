import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { getPortfolio } from "@/lib/portfolio/repo";
import { isSameOrigin } from "@/lib/request";

// Guardas comuns das rotas `app/api/portfolio/*` e `app/api/imports/*` (site.md §7.4):
// mesma origem (CSRF), sessão válida e a carteira **da pessoa da sessão** — nunca um id
// de carteira vindo do cliente.

export type PortfolioContext = { userId: string; portfolioId: string };

export async function requirePortfolio(
  request: Request,
): Promise<{ ok: true; ctx: PortfolioContext } | { ok: false; response: Response }> {
  if (!isSameOrigin(request.headers)) {
    return { ok: false, response: NextResponse.json({ error: "Origem inválida" }, { status: 403 }) };
  }
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) return { ok: false, response: NextResponse.json({ error: "Sessão expirada" }, { status: 401 }) };
  const portfolio = await getPortfolio(session.user.id);
  if (!portfolio) {
    return { ok: false, response: NextResponse.json({ error: "Crie a carteira primeiro" }, { status: 409 }) };
  }
  return { ok: true, ctx: { userId: session.user.id, portfolioId: portfolio.id } };
}
