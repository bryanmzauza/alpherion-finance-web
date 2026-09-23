"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

// Gaveta do menu no celular (plano 4.1). É um `<details>`: abre e fecha sem JavaScript,
// é acessível pelo teclado de fábrica e funciona antes da hidratação. O único JS aqui é
// fechar a gaveta quando a rota muda — o header persiste entre páginas, e sem isso a
// gaveta ficaria aberta por cima da página nova.
export function MobileMenu({ items }: { items: { href: string; label: string }[] }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    if (ref.current) ref.current.open = false;
  }, [pathname]);

  return (
    <details
      ref={ref}
      className="group relative lg:hidden"
      onKeyDown={(event) => {
        if (event.key === "Escape" && ref.current?.open) {
          ref.current.open = false;
          ref.current.querySelector("summary")?.focus();
        }
      }}
    >
      <summary className="flex h-9 cursor-pointer list-none items-center rounded-md border border-navy-3 px-3 text-table text-ice-70 hover:text-ice [&::-webkit-details-marker]:hidden">
        <span className="group-open:hidden">Menu</span>
        <span className="hidden group-open:inline">Fechar</span>
      </summary>
      <nav
        aria-label="Principal"
        className="absolute right-0 top-full z-50 mt-2 w-56 rounded-md border border-navy-3 bg-navy-2 py-2 shadow-xl"
      >
        <ul>
          {items.map((item) => (
            <li key={item.href}>
              <Link href={item.href} className="block px-4 py-2 text-ice-70 hover:bg-navy-3 hover:text-ice">
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </details>
  );
}
