import { NextResponse } from "next/server";
import { z } from "zod";
import { auth } from "@/lib/auth";
import { env } from "@/lib/env";
import { deleteTransaction } from "@/lib/portfolio/repo";
import { clientIp, isSameOrigin } from "@/lib/request";

// POST /api/portfolio/transactions/delete — formulário da lista de movimentações.
// `deleteTransaction` só apaga linha de carteira desta pessoa (IDOR: repo.int.test.ts).
const schema = z.object({ id: z.uuid() });

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request.headers)) return NextResponse.json({ error: "Origem inválida" }, { status: 403 });
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) return NextResponse.redirect(new URL("/entrar?next=/carteira/movimentacoes", env.APP_URL), 303);

  const form = await request.formData().catch(() => null);
  const parsed = schema.safeParse({ id: form?.get("id") });
  const back = new URL("/carteira/movimentacoes", env.APP_URL);
  if (!parsed.success) return NextResponse.redirect(back, 303);

  const deleted = await deleteTransaction(session.user.id, parsed.data.id, { ip: clientIp(request.headers) });
  back.searchParams.set(deleted ? "apagada" : "erro", "1");
  return NextResponse.redirect(back, 303);
}
