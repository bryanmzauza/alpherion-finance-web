import Image from "next/image";
import Link from "next/link";
import { SITE_NAME } from "@/content/site";

const NAV = [
  { href: "/raio-x", label: "Raio-X" },
  { href: "/videos", label: "Vídeos" },
  { href: "/sobre", label: "Sobre" },
  { href: "/contato", label: "Contato" },
];

export function Header() {
  return (
    <header className="border-b border-navy-3">
      <div className="mx-auto flex h-16 w-full max-w-site items-center justify-between px-4 md:px-6">
        <Link href="/" className="flex items-center gap-3" aria-label={`${SITE_NAME} — início`}>
          <Image src="/brand/marca-dagua.png" alt="" width={32} height={32} priority />
          <span className="font-display text-lg font-semibold tracking-wide">Alpherion Finance</span>
        </Link>
        <nav aria-label="Principal">
          <ul className="flex items-center gap-4 text-table sm:gap-6">
            {NAV.map((item) => (
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
