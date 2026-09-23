import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppHeader } from "@/components/app/app-header";
import { Disclaimer } from "@/components/ui/disclaimer";
import { requireSession } from "@/lib/session";

// App autenticado (site.md §2.2). A sessão é conferida aqui **e** em cada página e rota
// (o layout não roda de novo em toda navegação do cliente; a página roda).
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function AppLayout({ children }: { children: ReactNode }) {
  const session = await requireSession();
  return (
    <>
      <AppHeader email={session.user.email} />
      <main id="conteudo" className="flex-1">
        <div className="mx-auto w-full max-w-market px-4 py-10 md:px-6 md:py-14">{children}</div>
        <div className="mx-auto w-full max-w-market px-4 pb-16 md:px-6">
          <Disclaimer />
        </div>
      </main>
    </>
  );
}
