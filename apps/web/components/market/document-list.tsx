import type { MarketDocument } from "@/lib/market";
import { date } from "@/lib/format";

// Comunicados entregues à CVM (site.md §8.3).
//
// Título, categoria, data e **link para o documento na CVM**. Sem resumo, sem destaque,
// sem "o que isso significa": resumir fato relevante é interpretação, e interpretação é
// análise. O leitor clica e lê a fonte.
export function DocumentList({ documents }: { documents: MarketDocument[] }) {
  if (documents.length === 0) {
    return <p className="text-ice-70">Nenhum comunicado no período carregado.</p>;
  }

  return (
    <ul className="divide-y divide-navy-3 border-y border-navy-3">
      {documents.map((doc) => (
        <li key={doc.protocol} className="py-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="text-table uppercase tracking-wide text-gold">{doc.category}</span>
            <time className="text-table tabular-nums text-ice-70" dateTime={doc.delivered_at}>
              {date(doc.delivered_at)}
            </time>
          </div>
          <a
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 block underline decoration-ice-70/40 underline-offset-4 hover:decoration-ice"
          >
            {doc.subject ?? doc.type ?? doc.category}
          </a>
        </li>
      ))}
    </ul>
  );
}
