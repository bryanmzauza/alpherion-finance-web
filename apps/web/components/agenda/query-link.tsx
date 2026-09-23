"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";

// Link que leva a query atual junto (`?tipo=proventos&classe=fiis`): navegar de semana
// em semana na `/agenda` não pode perder o filtro escolhido. Antes da hidratação (e sem
// JS) é um link comum, sem a query.

type Props = { href: string; className?: string; children: ReactNode };

export function QueryLink(props: Props) {
  return (
    <Suspense fallback={<Link href={props.href} className={props.className}>{props.children}</Link>}>
      <WithQuery {...props} />
    </Suspense>
  );
}

function WithQuery({ href, className, children }: Props) {
  const query = useSearchParams().toString();
  const [path, hash] = href.split("#");
  const target = `${path}${query ? `?${query}` : ""}${hash ? `#${hash}` : ""}`;
  return (
    <Link href={target} className={className}>
      {children}
    </Link>
  );
}
