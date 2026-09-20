import type { Metadata } from "next";
import { LegalPage } from "@/components/site/legal-page";
import Doc, { frontmatter } from "@/content/legal/privacidade.mdx";

export const metadata: Metadata = {
  title: frontmatter.title,
  description: "Quais dados o Alpherion Finance coleta, para quê, com que base legal, por quanto tempo e com quem compartilha.",
  alternates: { canonical: "/privacidade" },
};

export default function PrivacidadePage() {
  return (
    <LegalPage meta={frontmatter} gold="Privacidade">
      <Doc />
    </LegalPage>
  );
}
