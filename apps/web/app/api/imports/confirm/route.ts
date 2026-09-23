import { NextResponse } from "next/server";
import { requirePortfolio } from "@/lib/portfolio/http";
import { confirmImport, confirmSchema } from "@/lib/portfolio/imports";
import { rateLimit } from "@/lib/rate-limit";
import { clientIp, userAgent } from "@/lib/request";

// POST /api/imports/confirm — grava a prévia que a pessoa conferiu (cifrada, com dedupe).
export async function POST(request: Request): Promise<Response> {
  const guard = await requirePortfolio(request);
  if (!guard.ok) return guard.response;
  const { userId, portfolioId } = guard.ctx;

  const rl = await rateLimit("imports-confirm", userId, 30, 3600);
  if (!rl.ok) return NextResponse.json({ error: "Muitas importações seguidas; tente daqui a pouco" }, { status: 429 });

  const parsed = confirmSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "Prévia inválida; envie os arquivos de novo" }, { status: 422 });

  const result = await confirmImport(userId, portfolioId, parsed.data, {
    ip: clientIp(request.headers),
    userAgent: userAgent(request.headers),
  });
  return NextResponse.json(result, { status: 201 });
}
