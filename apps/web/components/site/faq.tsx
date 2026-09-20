// FAQ sem JavaScript: <details>/<summary> é acessível por teclado e leitor de tela.
export function Faq({ items }: { items: { q: string; a: string }[] }) {
  return (
    <div className="divide-y divide-navy-3 rounded-lg border border-navy-3 bg-navy-2">
      {items.map((item) => (
        <details key={item.q} className="group px-6 py-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium text-ice [&::-webkit-details-marker]:hidden">
            {item.q}
            <span aria-hidden="true" className="text-gold transition-transform group-open:rotate-45">
              +
            </span>
          </summary>
          <p className="mt-3 text-ice-70">{item.a}</p>
        </details>
      ))}
    </div>
  );
}
