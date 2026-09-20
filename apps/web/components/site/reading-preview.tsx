import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SAMPLE_PORTFOLIO } from "@/content/site";

// Prévia estática de uma análise (landing, seção 3): a leitura de Exposição da carteira
// ilustrativa do vídeo 02, em HTML — acessível e sem imagem para manter.
export function ReadingPreview() {
  return (
    <figure className="mx-auto max-w-2xl">
      <Card className="relative overflow-hidden">
        <Badge tone="gold" className="absolute top-4 right-4">
          carteira ilustrativa
        </Badge>
        <p className="text-table text-ice-70">Exposição</p>
        <p className="mt-1 font-display text-xl font-semibold">A que você está exposto sem saber?</p>
        <div className="mt-6 grid gap-6 sm:grid-cols-[auto_1fr] sm:items-center">
          <div>
            <p className="tabular font-display text-6xl font-bold text-gold">0,96</p>
            <p className="mt-1 text-table text-ice-70">correlação da carteira com o Bitcoin</p>
          </div>
          <dl className="tabular grid grid-cols-2 gap-x-6 gap-y-2 text-table">
            <dt className="text-ice-70">Cripto</dt>
            <dd className="text-right">50%</dd>
            <dt className="text-ice-70">Juros Brasil</dt>
            <dd className="text-right">22%</dd>
            <dt className="text-ice-70">Bolsa Brasil</dt>
            <dd className="text-right">11%</dd>
            <dt className="text-ice-70">Dólar direto</dt>
            <dd className="text-right">9%</dd>
            <dt className="text-ice-70">Commodities</dt>
            <dd className="text-right">9%</dd>
          </dl>
        </div>
        <p className="mt-6 border-t border-navy-3 pt-4 text-ice-70">
          Se você me der só o preço do Bitcoin, eu digo quase exatamente o que essa carteira fez no dia. Os outros dez
          ativos existem, mas não mudam a forma do risco.
        </p>
      </Card>
      <figcaption className="mt-3 text-center text-xs text-ice-70">
        Carteira ilustrativa de {SAMPLE_PORTFOLIO.total} com 11 ativos, dados de 3 anos, referência{" "}
        {SAMPLE_PORTFOLIO.referenceDate}. Não é sugestão de alocação.
      </figcaption>
    </figure>
  );
}
