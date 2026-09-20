import { frontmatter as avisoLegal } from "@/content/legal/aviso-legal.mdx";
import { frontmatter as privacidade } from "@/content/legal/privacidade.mdx";
import { frontmatter as termos } from "@/content/legal/termos.mdx";

export type LegalDoc = "privacidade" | "termos" | "aviso-legal";

export type LegalFrontmatter = { title: string; version: string; date: string };

// Versões vigentes dos textos legais. O aceite (consents.document_version) grava daqui.
export const LEGAL: Record<LegalDoc, LegalFrontmatter> = {
  privacidade,
  termos,
  "aviso-legal": avisoLegal,
};

export const formatDate = (iso: string): string => {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
};
