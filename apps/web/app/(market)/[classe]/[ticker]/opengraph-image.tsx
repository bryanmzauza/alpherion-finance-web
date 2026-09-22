import { OG_CONTENT_TYPE, OG_SIZE, ogImage } from "@/lib/og";
import { getSecurity, optional } from "@/lib/market";

export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "Alpherion Finance";

// OG da página do ativo: **ticker dourado e nome da empresa. Sem cotação.**
//
// O plano previa a cotação na imagem; ela fica de fora de propósito. Redes sociais
// cacheiam a imagem de OG por dias e só a reprocessam quando querem — um preço ali
// vira exatamente o tipo de número velho sem data que o site inteiro evita, e num
// lugar onde não cabe `SourceBadge` nem "—" com motivo. Ticker e nome não envelhecem.
export default async function Image({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const code = ticker.toUpperCase();
  const detail = await optional(getSecurity(code));

  return ogImage({
    title: code,
    gold: code,
    subtitle: detail
      ? (detail.profile.trade_name ?? detail.profile.company_name)
      : "Dados. Insights. Patrimônio.",
  });
}
