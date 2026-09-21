// Bloco JSON-LD (schema.org). Tipo de script não executável: a CSP não o bloqueia.
// `<` vira \u003c para o JSON não fechar a tag por acidente.
export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\u003c") }}
    />
  );
}
