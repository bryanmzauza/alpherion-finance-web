import type { ReactNode } from "react";
import { Footer } from "@/components/site/footer";
import { Header } from "@/components/site/header";
import { SkipLink } from "@/components/site/skip-link";
import { Disclaimer } from "@/components/ui/disclaimer";

// Mesmo enquadramento do site público, com o container largo das páginas de ativo (§5).
// O disclaimer fica no fim de toda página de mercado: dado de mercado com fonte é
// informação, não análise — e o texto do §8.3 é o que registra essa diferença.
export default function MarketLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SkipLink />
      <Header />
      <main id="conteudo" className="flex-1">
        {children}
        <div className="mx-auto w-full max-w-market px-4 pb-16 md:px-6">
          <Disclaimer />
        </div>
      </main>
      <Footer />
    </>
  );
}
