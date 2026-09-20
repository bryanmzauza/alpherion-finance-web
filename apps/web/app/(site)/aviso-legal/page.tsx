import type { Metadata } from "next";
import { LegalPage } from "@/components/site/legal-page";
import Doc, { frontmatter } from "@/content/legal/aviso-legal.mdx";

export const metadata: Metadata = {
  title: frontmatter.title,
  description: "Aviso legal do Alpherion Finance: conteúdo educacional, sem recomendação de investimento; situação regulatória perante a CVM.",
  alternates: { canonical: "/aviso-legal" },
};

export default function AvisoLegalPage() {
  return (
    <LegalPage meta={frontmatter} gold="legal">
      <Doc />
    </LegalPage>
  );
}
