import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Props = HTMLAttributes<HTMLElement> & {
  /** Título da seção (H2). Usar <Gold> para no máximo uma palavra. */
  heading?: ReactNode;
  intro?: ReactNode;
  wide?: boolean;
};

// Container 1120 (1280 com `wide`, para páginas de ativo/screener) — §5.
export function Section({ heading, intro, wide, className, children, ...props }: Props) {
  return (
    <section className={cn("py-16 md:py-20", className)} {...props}>
      <div className={cn("mx-auto w-full px-4 md:px-6", wide ? "max-w-market" : "max-w-site")}>
        {heading ? <h2>{heading}</h2> : null}
        {intro ? <p className="mt-4 max-w-2xl text-ice-70">{intro}</p> : null}
        <div className={cn(heading || intro ? "mt-8" : undefined)}>{children}</div>
      </div>
    </section>
  );
}
