import type { MDXComponents } from "mdx/types";

// Estilo dos textos legais (content/legal/*.mdx). Sem H1 no MDX: o título vem da página.
export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h2: (props) => <h2 className="mt-12 mb-4 text-h2" {...props} />,
    h3: (props) => <h3 className="mt-8 mb-3 text-xl font-semibold" {...props} />,
    p: (props) => <p className="my-4 text-ice-70" {...props} />,
    ul: (props) => <ul className="my-4 list-disc space-y-2 pl-6 text-ice-70" {...props} />,
    ol: (props) => <ol className="my-4 list-decimal space-y-2 pl-6 text-ice-70" {...props} />,
    a: (props) => <a className="text-gold underline-offset-4 hover:underline" {...props} />,
    strong: (props) => <strong className="font-semibold text-ice" {...props} />,
    table: (props) => (
      <div className="my-6 overflow-x-auto rounded-lg border border-navy-3">
        <table className="w-full text-table" {...props} />
      </div>
    ),
    th: (props) => <th className="border-b border-navy-3 bg-navy-2 px-3 py-2 text-left font-medium" {...props} />,
    td: (props) => <td className="border-b border-navy-3 px-3 py-2 align-top text-ice-70" {...props} />,
    ...components,
  };
}
