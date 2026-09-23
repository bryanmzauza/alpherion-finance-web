import Image from "next/image";
import Link from "next/link";
import { SITE_NAME } from "@/content/site";
import { env } from "@/lib/env";

// Cabeçalho do app: marca, navegação da carteira e "Sair" (formulário POST — sair por
// GET deixaria qualquer imagem de terceiro deslogar a pessoa).
const NAV = [
  { href: "/carteira", label: "Carteira" },
  { href: "/carteira/movimentacoes", label: "Movimentações" },
  { href: "/carteira/proventos", label: "Proventos" },
  { href: "/carteira/importar/b3", label: "Importar" },
];

export function AppHeader({ email }: { email: string }) {
  return (
    <header className="border-b border-navy-3">
      <div className="mx-auto flex h-16 w-full max-w-market items-center gap-4 px-4 md:px-6">
        <Link href="/carteira" className="flex shrink-0 items-center gap-3" aria-label={`${SITE_NAME} — carteira`}>
          <Image src="/brand/marca-dagua.png" alt="" width={32} height={32} priority />
          <span className="hidden font-display text-lg font-semibold tracking-wide sm:inline">Alpherion Finance</span>
        </Link>
        <div className="ml-auto flex items-center gap-4 text-table">
          <a href={`${env.SITE_URL}/mercado`} className="hidden text-ice-70 hover:text-ice md:inline">
            Mercado
          </a>
          <span className="hidden max-w-48 truncate text-ice-70 lg:inline" title={email}>
            {email}
          </span>
          <form action="/api/sair" method="post">
            <button type="submit" className="text-ice-70 hover:text-ice">
              Sair
            </button>
          </form>
        </div>
      </div>
      <nav aria-label="Carteira" className="border-t border-navy-3">
        <ul className="mx-auto flex h-11 w-full max-w-market items-center gap-6 overflow-x-auto px-4 text-table md:px-6">
          {NAV.map((item) => (
            <li key={item.href} className="shrink-0">
              <Link href={item.href} className="text-ice-70 transition-colors hover:text-ice">
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
