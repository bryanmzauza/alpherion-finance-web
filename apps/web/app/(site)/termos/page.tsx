import type { Metadata } from "next";
import { LegalPage } from "@/components/site/legal-page";
import Doc, { frontmatter } from "@/content/legal/termos.mdx";

export const metadata: Metadata = {
  title: frontmatter.title,
  description: "Termos de uso do site, do aplicativo e da lista de e-mail do Alpherion Finance.",
  alternates: { canonical: "/termos" },
};

export default function TermosPage() {
  return (
    <LegalPage meta={frontmatter} gold="Uso">
      <Doc />
    </LegalPage>
  );
}
