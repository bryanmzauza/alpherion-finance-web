import { buttonVariants } from "@/components/ui/button";
import { env } from "@/lib/env";

// CTA da página do ativo (§2.1). Pergunta, não indica: "tem na carteira?" convida a
// diagnosticar o que a pessoa já tem — nunca "compre", nunca "adicione à sua carteira".
export function AssetCTA({ ticker }: { ticker: string }) {
  return (
    <aside className="rounded-lg border border-navy-3 bg-navy-2 p-6">
      <p className="text-h2 font-display">Tem {ticker} na carteira?</p>
      <p className="mt-2 text-ice-70">
        O Alpherion lê a sua carteira inteira e devolve cinco leituras de risco — concentração,
        correlação, exposição, drawdown e liquidez. Não diz o que comprar.
      </p>
      <a href={`${env.APP_URL}/carteira`} className={`${buttonVariants()} mt-4`}>
        Analisar minha carteira
      </a>
    </aside>
  );
}
