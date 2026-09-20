import Link from "next/link";
import { Footer } from "@/components/site/footer";
import { Header } from "@/components/site/header";
import { buttonVariants } from "@/components/ui/button";
import { Gold } from "@/components/ui/gold";

// 404 do site. A busca de ticker entra na Etapa 3, junto com as páginas de ativo.
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
        <Link href="/" className={`${buttonVariants({ variant: "secondary" })} mt-8 self-start`}>
          Voltar ao início
        </Link>
      </main>
      <Footer />
    </>
  );
}
