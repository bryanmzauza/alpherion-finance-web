import { NextResponse } from "next/server";
import { z } from "zod";
import { MAX_QUERY, MIN_QUERY } from "@/lib/asset-search";
import { searchAssets } from "@/lib/market";
import { rateLimit } from "@/lib/rate-limit";
import { clientIp } from "@/lib/request";

// GET /api/market/search?q= — ponte da busca do header para `GET /v1/assets/search`
// (site.md §2.1, plano 4.1).
//
// Existe porque o token de serviço da API não pode ir para o navegador (§3.2): quem fala
// com a API é o servidor do `web`. Rate limit 30/min/IP no Redis (a Cloudflare tem o
// segundo). Sem cookie, sem sessão, sem log do termo buscado — o termo não é dado
// pessoal, mas também não serve para nada guardado.

const LIMIT_PER_MINUTE = 30;

const querySchema = z.string().trim().min(MIN_QUERY).max(MAX_QUERY);

export async function GET(request: Request): Promise<Response> {
  const parsed = querySchema.safeParse(new URL(request.url).searchParams.get("q") ?? "");
  if (!parsed.success) {
    return NextResponse.json({ error: "Busca precisa de 2 a 60 caracteres" }, { status: 400 });
  }

  const rl = await rateLimit("search", clientIp(request.headers), LIMIT_PER_MINUTE, 60);
  if (!rl.ok) {
    return NextResponse.json(
      { error: "Muitas buscas seguidas" },
      { status: 429, headers: { "Retry-After": "60" } },
    );
  }

  try {
    const result = await searchAssets(parsed.data);
    return NextResponse.json(result, {
      headers: {
        // O resultado é o mesmo para todo mundo e muda com a carga do dia.
        "Cache-Control": "public, max-age=60, s-maxage=300",
        "X-Robots-Tag": "noindex",
      },
    });
  } catch {
    console.error("[search] API indisponível");
    return NextResponse.json({ error: "Busca indisponível" }, { status: 502 });
  }
}
