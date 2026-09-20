import type { HTMLAttributes, TableHTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Tabela larga rola dentro do card, nunca a página (§5). Sempre com <caption>.
export function Table({ className, caption, ...props }: TableHTMLAttributes<HTMLTableElement> & { caption: string }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-navy-3 bg-navy-2">
      <table className={cn("w-full text-table", className)} {...props}>
        <caption className="sr-only">{caption}</caption>
        {props.children}
      </table>
    </div>
  );
}

export function Thead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className="text-left text-ice-70" {...props} />;
}

export function Tr({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("border-b border-navy-3 last:border-0", className)} {...props} />;
}

export function Th({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th scope="col" className={cn("px-4 py-3 font-medium", className)} {...props} />;
}

export function Td({ className, numeric, ...props }: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return <td className={cn("px-4 py-3", numeric && "text-right", className)} {...props} />;
}
