import Image from "next/image";
import Link from "next/link";
import { MarketStrip } from "@/components/market/market-strip";
import { MobileMenu } from "@/components/site/mobile-menu";
import { SearchBox } from "@/components/search/search-box";
import { SITE_NAME } from "@/content/site";
import { PORTAL_NAV } from "@/lib/market-classes";

// Header de toda página de alpherion.com.br (site.md §2.1, plano 4.1): faixa de mercado,
// busca global e o menu do portal. No celular o menu vira gaveta (`MobileMenu`).
//
// O que cada parte custa em JS no cliente, porque a landing tem orçamento (§9):
// - `MarketStrip`: nada (server component);
// - `SearchBox`: a casca do campo; o resto da busca só baixa no foco;
// - `MobileMenu`: fechar a gaveta ao navegar.
export function Header() {
  return (
    <header>
      <MarketStrip />
      <div className="border-b border-navy-3">
        <div className="mx-auto flex h-16 w-full max-w-site items-center gap-4 px-4 md:px-6">
          <Link href="/" className="flex shrink-0 items-center gap-3" aria-label={`${SITE_NAME} — início`}>
            <Image src="/brand/marca-dagua.png" alt="" width={32} height={32} priority />
            <span className="hidden font-display text-lg font-semibold tracking-wide sm:inline">
              Alpherion Finance
            </span>
          </Link>
          <SearchBox className="ml-auto w-full max-w-sm" />
          <MobileMenu items={PORTAL_NAV} />
        </div>
        <nav aria-label="Principal" className="hidden border-t border-navy-3 lg:block">
          <ul className="mx-auto flex h-11 w-full max-w-site items-center gap-6 px-6 text-table">
            {PORTAL_NAV.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="text-ice-70 transition-colors hover:text-ice">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
