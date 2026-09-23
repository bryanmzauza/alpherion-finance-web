import Link from "next/link";
import type { SectorNode } from "@/lib/market";

// Árvore setor → subsetor → segmento da classificação B3, e os segmentos de FII
// (site.md §2.1, plano 4.4) — estes, o `Segmento_Atuacao` do informe mensal da CVM. A contagem é o número de papéis ativos — "23 papéis", sem
// adjetivo. A ordem é a alfabética da própria classificação: nenhum setor vem "antes"
// por mérito.

const NUMBER = new Intl.NumberFormat("pt-BR");

type Tree = Map<string, Map<string, SectorNode[]>>;

function build(nodes: SectorNode[]): Tree {
  const tree: Tree = new Map();
  for (const node of nodes) {
    const sector = node.sector ?? "Sem setor informado";
    const subsector = node.subsector ?? sector;
    if (!tree.has(sector)) tree.set(sector, new Map());
    const subs = tree.get(sector)!;
    if (!subs.has(subsector)) subs.set(subsector, []);
    subs.get(subsector)!.push(node);
  }
  return tree;
}

const papers = (n: number) => `${NUMBER.format(n)} ${n === 1 ? "papel" : "papéis"}`;

export function SectorTree({ nodes }: { nodes: SectorNode[] }) {
  const b3 = build(nodes.filter((n) => n.kind === "b3_segment"));
  const fii = nodes.filter((n) => n.kind === "fii_segment");

  return (
    <div className="grid gap-12 lg:grid-cols-[2fr_1fr]">
      <section aria-labelledby="classificacao-b3">
        <h2 id="classificacao-b3">Classificação setorial da B3</h2>
        <p className="mt-2 text-table text-ice-70">Setor, subsetor e segmento, como a B3 classifica cada empresa.</p>
        <ul className="mt-6 space-y-6">
          {[...b3.entries()].map(([sector, subs]) => {
            const total = [...subs.values()].flat().reduce((sum, n) => sum + n.securities_count, 0);
            return (
              <li key={sector} className="rounded-lg border border-navy-3 bg-navy-2 p-4">
                <p className="flex items-baseline justify-between gap-4">
                  <span className="font-display text-lg font-semibold">{sector}</span>
                  <span className="text-table text-ice-70 tabular-nums">{papers(total)}</span>
                </p>
                <ul className="mt-3 space-y-3">
                  {[...subs.entries()].map(([subsector, segments]) => (
                    <li key={subsector}>
                      <p className="text-table text-ice-70">{subsector}</p>
                      <ul className="mt-1 flex flex-wrap gap-2">
                        {segments.map((segment) => (
                          <SegmentLink key={segment.slug} node={segment} />
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="segmentos-fii">
        <h2 id="segmentos-fii">Segmentos de FII</h2>
        <p className="mt-2 text-table text-ice-70">O segmento de atuação que cada fundo declara à CVM no informe mensal.</p>
        {fii.length > 0 ? (
          <ul className="mt-6 flex flex-wrap gap-2">
            {fii.map((segment) => (
              <SegmentLink key={segment.slug} node={segment} />
            ))}
          </ul>
        ) : (
          <p className="mt-6 text-table text-ice-70">Nenhum segmento de FII carregado.</p>
        )}
      </section>
    </div>
  );
}

function SegmentLink({ node }: { node: SectorNode }) {
  return (
    <li>
      <Link
        href={`/setores/${node.slug}`}
        className="inline-flex items-baseline gap-2 rounded-full border border-navy-3 px-3 py-1 text-table hover:border-gold"
      >
        {node.name}
        <span className="text-xs text-ice-70 tabular-nums">{NUMBER.format(node.securities_count)}</span>
      </Link>
    </li>
  );
}
