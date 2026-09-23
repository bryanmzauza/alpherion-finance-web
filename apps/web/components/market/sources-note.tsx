import type { SourceRef } from "@/lib/market";

// Rodapé de fontes de uma página de mercado (§8.10): quem publicou cada número desta
// página, sem repetir, e o aviso de que dado de terceiro pode ter erro ou atraso.
// Aceita o `SourceRef` de um bloco ou a atribuição em texto, para fontes cujos números
// chegam sem bloco próprio (os indicadores de uma linha de tabela vêm da CVM).
export function SourcesNote({ sources }: { sources: (SourceRef | string | null | undefined)[] }) {
  const unique = [
    ...new Set(sources.filter(Boolean).map((s) => (typeof s === "string" ? s : s!.attribution))),
  ];
  if (unique.length === 0) return null;
  return (
    <p className="mt-12 border-t border-navy-3 pt-6 text-table text-ice-70">
      Fontes desta página: {unique.join(" · ")}. Dados podem conter erros ou atrasos; confira
      sempre na fonte.
    </p>
  );
}
