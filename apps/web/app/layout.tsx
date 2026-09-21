import type { Metadata, Viewport } from "next";
import { Analytics } from "@/components/site/analytics";
import { SITE_DESCRIPTION, SITE_NAME } from "@/content/site";
import { env } from "@/lib/env";
import { inter, playfair } from "./fonts";
import "./globals.css";

// Metadata base (site.md §9). SITE_URL precisa existir no build (Dockerfile: ARG SITE_URL),
// porque URLs canônicas, OG e sitemap são resolvidas contra ela.
export const metadata: Metadata = {
  metadataBase: new URL(env.SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  openGraph: { type: "website", locale: "pt_BR", siteName: SITE_NAME },
  twitter: { card: "summary_large_image" },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#0B192C",
  colorScheme: "dark",
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
