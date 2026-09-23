import { NextResponse } from "next/server";
import { requirePortfolio } from "@/lib/portfolio/http";
import { manualTransactionSchema } from "@/lib/portfolio/input";
import { addTransactions } from "@/lib/portfolio/repo";
import { rateLimit } from "@/lib/rate-limit";

// POST /api/portfolio/transactions — lançamento manual (`/carteira/adicionar`).
export async function POST(request: Request): Promise<Response> {
  const guard = await requirePortfolio(request);
  if (!guard.ok) return guard.response;
  const { userId, portfolioId } = guard.ctx;

  const rl = await rateLimit("portfolio-write", userId, 120, 600);
  if (!rl.ok) return NextResponse.json({ error: "Muitos lançamentos seguidos; espere alguns minutos" }, { status: 429 });

  const parsed = manualTransactionSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ error: "Confira os campos", issues: parsed.error.issues.map((i) => i.path.join(".")) }, { status: 422 });
  }
  const t = parsed.data;
  await addTransactions(
    userId,
    portfolioId,
    [
      {
        asset: { symbol: t.asset.symbol, name: t.asset.name, assetClass: t.asset.asset_class, marketRef: t.asset.market_ref },
        date: t.date,
        side: t.side,
        quantity: t.quantity,
        price: t.price,
        fees: t.fees,
        note: t.note ?? null,
      },
    ],
    { source: "manual" },
  );
  return NextResponse.json({ ok: true }, { status: 201 });
}
