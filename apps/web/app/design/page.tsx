import { notFound } from "next/navigation";
import { ReadingCard } from "@/components/site/reading-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Disclaimer } from "@/components/ui/disclaimer";
import { Input } from "@/components/ui/input";
import { Tooltip } from "@/components/ui/tooltip";
import { READINGS } from "@/content/site";

// Guia de estilo dos tokens do §5. Só existe em dev (site.md §5: "rota só em dev").
const colors = [
  ["navy", "Fundo padrão", "bg-navy"],
  ["navy-2", "Superfícies elevadas (cards, inputs)", "bg-navy-2"],
  ["navy-3", "Bordas, divisores, hover", "bg-navy-3"],
  ["gold", "Acento: uma palavra por título, botão primário, números-chave", "bg-gold"],
  ["gold-2", "Hover do dourado", "bg-gold-2"],
  ["ice", "Texto principal", "bg-ice"],
  ["ice-70", "Texto secundário, fontes e datas", "bg-ice-70"],
  ["ok", "Semântica de risco: ok (sempre com sinal/ícone + texto)", "bg-ok"],
  ["warn", "Semântica de risco: atenção", "bg-warn"],
  ["risk", "Semântica de risco: risco", "bg-risk"],
] as const;

const sampleRows = [
  ["Concentração", "38%", "maior posição"],
  ["Correlação", "0,91", "média entre pares"],
  ["Exposição", "0,96", "beta ao Ibovespa"],
  ["Drawdown", "−34,4%", "pior queda em 5 anos"],
  ["Liquidez", "0,03%", "do volume diário"],
];

export default function DesignPage() {
  if (process.env.NODE_ENV === "production") notFound();

  return (
    <main className="mx-auto w-full max-w-site px-4 py-12 md:px-6">
      <h1>
        Guia de <span className="text-gold">estilo</span>
      </h1>
      <p className="mt-2 text-ice-70">Tokens do site.md §5. Rota disponível só em desenvolvimento.</p>

      <section className="mt-12">
        <h2>Cores</h2>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2">
          {colors.map(([name, use, cls]) => (
            <li key={name} className="flex items-center gap-4 rounded-lg border border-navy-3 bg-navy-2 p-3">
              <span className={`h-12 w-12 shrink-0 rounded-md border border-navy-3 ${cls}`} aria-hidden />
              <div>
                <code className="text-table">--color-{name}</code>
                <p className="text-table text-ice-70">{use}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12">
        <h2>Tipografia</h2>
        <div className="mt-6 space-y-6 rounded-lg border border-navy-3 bg-navy-2 p-6">
          <div>
            <p className="text-table text-ice-70">H1 · Playfair Display 600 · 40/48 · no máximo uma palavra dourada</p>
            <h1 className="mt-1">
              Você sabe o que <span className="text-gold">tem</span>?
            </h1>
          </div>
          <div>
            <p className="text-table text-ice-70">H2 · Playfair Display 600 · 28/36</p>
            <h2 className="mt-1">As cinco leituras</h2>
          </div>
          <div>
            <p className="text-table text-ice-70">Corpo · Inter 400 · 16/26</p>
            <p className="mt-1 max-w-2xl">
              O Alpherion lê a sua carteira e devolve cinco leituras de risco. Não é recomendação. Não
              considera seu perfil. Não indica compra ou venda.
            </p>
          </div>
          <div>
            <p className="text-table text-ice-70">Número de destaque · Playfair Display 700 · dourado</p>
            <p className="tabular mt-1 font-display text-5xl font-bold text-gold">38%</p>
          </div>
        </div>
      </section>

      <section className="mt-12">
        <h2>Componentes</h2>
        <div className="mt-6 space-y-8 rounded-lg border border-navy-3 bg-navy-2 p-6">
          <div className="flex flex-wrap items-center gap-3">
            <Button>Primário</Button>
            <Button variant="secondary">Secundário</Button>
            <Button variant="ghost">Ghost</Button>
            <Button disabled>Desabilitado</Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input placeholder="seu@email.com" aria-label="Exemplo de input" />
            <Checkbox id="design-check" label="Checkbox nunca pré-marcado, com label associado." />
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge>neutro</Badge>
            <Badge tone="gold">dourado</Badge>
            <Badge tone="ok">✓ ok</Badge>
            <Badge tone="warn">● atenção</Badge>
            <Badge tone="risk">▲ risco</Badge>
          </div>
          <p className="text-ice-70">
            Termo com definição:{" "}
            <Tooltip content="A maior queda do topo ao fundo em um período.">drawdown</Tooltip> (hover, foco ou toque; Esc fecha).
          </p>
          <div className="max-w-sm">
            <ReadingCard reading={READINGS[3]!} />
          </div>
          <Disclaimer />
        </div>
      </section>

      <section className="mt-12">
        <h2>Tabela</h2>
        <p className="mt-2 text-ice-70">Inter 14/22, números tabulares. Valores da carteira ilustrativa do vídeo 02.</p>
        <div className="mt-6 overflow-x-auto rounded-lg border border-navy-3 bg-navy-2">
          <table className="w-full text-table">
            <thead className="text-left text-ice-70">
              <tr className="border-b border-navy-3">
                <th className="px-4 py-3 font-medium">Leitura</th>
                <th className="px-4 py-3 text-right font-medium">Valor</th>
                <th className="px-4 py-3 font-medium">O que mede</th>
              </tr>
            </thead>
            <tbody>
              {sampleRows.map(([name, value, desc]) => (
                <tr key={name} className="border-b border-navy-3 last:border-0">
                  <td className="px-4 py-3">{name}</td>
                  <td className="px-4 py-3 text-right">{value}</td>
                  <td className="px-4 py-3 text-ice-70">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
