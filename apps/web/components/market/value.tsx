import type { ReactNode } from "react";
import { DASH } from "@/lib/format";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";

type Props = {
  /** Texto já formatado. `DASH` quando o valor é ausente. */
  children: ReactNode;
  /** Por que está ausente — vem de `missing_reasons` da API. */
  reason?: string;
  className?: string;
};

// O "—" do site.md §3.5: valor ausente **nunca** vira zero, e o motivo fica no tooltip.
//
// Duas coisas que este componente resolve de uma vez:
//
// - o leitor entende a diferença entre "a empresa não publicou" e "o indicador deu
//   zero" — que é a diferença entre confiar e não confiar no número ao lado;
// - o motivo chega como texto da API, não como frase inventada no front: quem sabe por
//   que o número falta é quem tentou calculá-lo.
//
// Sem motivo, o traço aparece sozinho — é o caso em que nem a API sabe dizer, e inventar
// uma explicação seria pior que a omissão.
export function Value({ children, reason, className }: Props) {
  const missing = children === DASH || children === null || children === undefined;

  if (missing && reason) {
    return (
      <Tooltip content={reason} className={className}>
        <span className="text-ice-70" aria-label={`Indisponível: ${reason}`}>
          {DASH}
        </span>
      </Tooltip>
    );
  }
  return (
    <span className={cn(missing && "text-ice-70", className)}>{missing ? DASH : children}</span>
  );
}
