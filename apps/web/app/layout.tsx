import type { Metadata } from "next";
import { Analytics } from "@/components/site/analytics";
import { inter, playfair } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Alpherion Finance",
    template: "%s · Alpherion Finance",
  },
  description:
    "O Alpherion lê a sua carteira — cripto, ações, FIIs, renda fixa — e devolve cinco leituras de risco, em português. Não diz o que comprar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${playfair.variable} ${inter.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
