import Link from "next/link";
import { Footer } from "@/components/site/footer";
import { Header } from "@/components/site/header";
import { SearchBox } from "@/components/search/search-box";
import { buttonVariants } from "@/components/ui/button";
import { Gold } from "@/components/ui/gold";
import { MARKET_LINKS } from "@/lib/market-classes";

// 404 do site. Quem caiu num ticker que não existe quase sempre queria outro papel: a
// busca em destaque e os caminhos de mercado resolvem melhor que um beco sem saída
// (site.md §2.1: "ticker inexistente → 404 com busca").
export default function NotFound() {
  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-site flex-1 flex-col justify-center px-4 py-24 md:px-6">
        <p className="text-table text-ice-70">Erro 404</p>
        <h1 className="mt-2">
          Página não <Gold>encontrada</Gold>
        </h1>
        <p className="mt-6 max-w-xl text-ice-70">O endereço pode ter mudado ou nunca existiu.</p>

        <SearchBox size="lg" className="mt-8 max-w-xl" />

        <nav aria-label="Dados de mercado" className="mt-8">
          <p className="text-table text-ice-70">Ou comece por uma classe:</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {MARKET_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="inline-block rounded-full border border-navy-3 px-4 py-2 text-table hover:border-gold hover:text-gold"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <Link href="/" className={`${buttonVariants({ variant: "secondary" })} mt-8 self-start`}>
          Voltar ao início
        </Link>
      </main>
      <Footer />
    </>
  );
}
