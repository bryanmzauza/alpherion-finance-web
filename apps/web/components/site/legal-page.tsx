import type { ReactNode } from "react";
import { Section } from "@/components/site/section";
import { Gold } from "@/components/ui/gold";
import { formatDate, type LegalFrontmatter } from "@/lib/legal";

// Moldura dos textos legais: título com a palavra dourada, versão e data do MDX.
export function LegalPage({ meta, gold, children }: { meta: LegalFrontmatter; gold: string; children: ReactNode }) {
  const [before, after] = meta.title.split(gold);
  return (
    <Section className="pt-20 md:pt-28">
      <h1 className="max-w-3xl">
        {before}
        <Gold>{gold}</Gold>
        {after}
      </h1>
      <p className="mt-4 text-table text-ice-70">
        Versão {meta.version} · {formatDate(meta.date)}
      </p>
      <article className="mt-10 max-w-3xl">{children}</article>
    </Section>
  );
}
