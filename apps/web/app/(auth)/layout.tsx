import type { Metadata } from "next";
import Image from "next/image";
import type { ReactNode } from "react";
import { SITE_NAME } from "@/content/site";
import { env } from "@/lib/env";

// Entrada no app (site.md §2.2): tela enxuta, sem o menu do portal — a pessoa veio
// entrar, não navegar. O logo leva de volta ao site público.
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="border-b border-navy-3">
        <div className="mx-auto flex h-16 w-full max-w-site items-center px-4 md:px-6">
          <a href={env.SITE_URL} className="flex items-center gap-3" aria-label={`${SITE_NAME} — site`}>
            <Image src="/brand/marca-dagua.png" alt="" width={32} height={32} priority />
            <span className="font-display text-lg font-semibold tracking-wide">Alpherion Finance</span>
          </a>
        </div>
      </header>
      <main id="conteudo" className="flex flex-1 items-start justify-center px-4 py-16 md:py-24">
        <div className="w-full max-w-md">{children}</div>
      </main>
    </>
  );
}
