import type { SourceRef } from "@/lib/market";
import { dateLong } from "@/lib/format";
import { cn } from "@/lib/cn";

type Props = {
  source: SourceRef;
  className?: string;
};

// A regra do §5: **nenhum número de mercado sem `SourceBadge`**. Fonte, documento ou
// período e data da carga — os três, porque "Fonte: CVM" sozinho não diz se o número é
// de 2025 ou de 2019, e é exatamente isso que o leitor precisa saber para conferir.
//
// A atribuição vem da API (`data_sources.attribution`), não do front: é a mesma string
// que a licença de cada fonte exige, e ela muda com a licença, não com o layout.
export function SourceBadge({ source, className }: Props) {
  const parts = [source.attribution, source.document].filter(Boolean);
  return (
    <p className={cn("text-table text-ice-70", className)}>
      {parts.join(" · ")}
      {source.updated_at ? ` · atualizado em ${dateLong(source.updated_at)}` : null}
    </p>
  );
}
