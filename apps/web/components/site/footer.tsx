import Image from "next/image";
import Link from "next/link";
import { Disclaimer } from "@/components/ui/disclaimer";
import { DATA_SOURCES, EMAILS, LEGAL_ENTITY, SITE_NAME } from "@/content/site";

const LEGAL_LINKS = [
  { href: "/privacidade", label: "Privacidade" },
  { href: "/termos", label: "Termos de uso" },
  { href: "/aviso-legal", label: "Aviso legal" },
  { href: "/contato", label: "Contato" },
];

// Rodapé (§5, item 10; §8.6: identificação do fornecedor desde o dia 1).
export function Footer() {
  return (
    <footer className="mt-24 border-t border-navy-3">
      <div className="mx-auto w-full max-w-site px-4 py-12 md:px-6">
        <div className="grid gap-10 md:grid-cols-[1fr_auto]">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Image src="/brand/marca-dagua.png" alt="" width={28} height={28} />
              <span className="font-display text-lg font-semibold tracking-wide">{SITE_NAME}</span>
            </div>
            <address className="text-table text-ice-70 not-italic">
              {LEGAL_ENTITY.razaoSocial} · CNPJ {LEGAL_ENTITY.cnpj} · {LEGAL_ENTITY.cidadeUf}
              <br />
              Contato:{" "}
              <a href={`mailto:${EMAILS.contato}`} className="hover:text-ice">
                {EMAILS.contato}
              </a>{" "}
              · Privacidade e encarregado (LGPD):{" "}
              <a href={`mailto:${EMAILS.privacidade}`} className="hover:text-ice">
                {EMAILS.privacidade}
              </a>
            </address>
          </div>
          <nav aria-label="Legal">
            <ul className="flex flex-wrap gap-x-6 gap-y-2 text-table">
              {LEGAL_LINKS.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-ice-70 hover:text-ice">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <Disclaimer className="mt-10" />

        <p className="mt-6 text-xs text-ice-70">
          Dados de mercado: {DATA_SOURCES.join(" · ")}. Podem conter erros ou atrasos; confira sempre na fonte.
        </p>
        <p className="mt-2 text-xs text-ice-70">© 2026 {SITE_NAME}</p>
      </div>
    </footer>
  );
}
