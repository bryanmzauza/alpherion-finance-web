import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { SORT_LABELS, SORT_PRESETS, sortTitle, type SortField } from "@/lib/market-sort";
import { MARKET_CLASSES, PORTAL_NAV } from "@/lib/market-classes";

// Lint de conteúdo (plano 4.5, ADR-018): **diagnóstico não é recomendação**. Nenhum
// texto do site pode chamar papel de "melhor", "barato", "oportunidade", dar preço-alvo
// ou mandar comprar — nem em título de preset, nem em texto de página, nem no conteúdo.
//
// O vocabulário é o do juízo de valor. Negação explícita na mesma frase é aceita, porque
// o aviso legal precisa dizer "não há preço-alvo nem preço justo"; o que o teste pega é
// a afirmação. "Pior mês" (um fato sobre uma série) não entra: a lista é de adjetivos
// sobre ativos, não de palavras comuns.

const FORBIDDEN: RegExp[] = [
  /\bmelhores\b/i,
  /\bpiores\b/i,
  /\bbarat[ao]s?\b/i,
  /\bcar[ao]s? demais\b/i,
  /\boportunidades?\b/i,
  /\bimperd[ií]ve(l|is)\b/i,
  /\bpreço[- ]justo\b/i,
  /\bpreço[- ]alvo\b/i,
  /\bpotencial de valoriza/i,
  /\bsubvalorizad/i,
  /\bdescontad[ao]s?\b/i,
  /\brecomendad[ao]s?\b/i,
  /\bcompre\b/i,
  /\bpara comprar\b/i,
];

const NEGATION = /\b(não|nem|nenhum|nenhuma|nunca|sem)\b/i;

const ROOT = path.resolve(__dirname, "..");

/** Onde mora texto que o leitor vê: conteúdo, páginas e componentes do site público. */
const SCANNED = [
  "content",
  "app/(site)",
  "app/(market)",
  "app/not-found.tsx",
  "components/market",
  "components/agenda",
  "components/search",
  "components/site",
  "lib/market-classes.ts",
  "lib/market-sort.ts",
  "lib/event-view.ts",
  "lib/asset-search.ts",
];

function files(entry: string): string[] {
  const full = path.join(ROOT, entry);
  if (statSync(full).isFile()) return [full];
  return readdirSync(full).flatMap((name) => files(path.join(entry, name)));
}

/** Tira comentários de código: o comentário explica a regra e cita o que é proibido. */
function visibleText(file: string): string {
  const source = readFileSync(file, "utf8");
  if (!/\.(tsx?|mjs)$/.test(file)) return source;
  return source
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
}

function violations(text: string): string[] {
  // Frase a frase: a negação só vale dentro da mesma frase.
  return text
    .split(/(?<=[.!?\n])/)
    .filter((sentence) => FORBIDDEN.some((re) => re.test(sentence)) && !NEGATION.test(sentence))
    .map((sentence) => sentence.trim());
}

describe("lint de conteúdo: nenhum juízo de valor sobre ativo", () => {
  const all = SCANNED.flatMap(files).filter((file) => /\.(tsx?|json|mdx?)$/.test(file) && !file.endsWith(".test.ts"));

  it("varre os arquivos esperados", () => {
    expect(all.length).toBeGreaterThan(30);
  });

  for (const file of all) {
    it(path.relative(ROOT, file), () => {
      expect(violations(visibleText(file))).toEqual([]);
    });
  }

  it("o detector pega a afirmação e deixa passar a negação", () => {
    expect(violations("As melhores ações para 2027.")).toHaveLength(1);
    expect(violations("PETR4 está barata.")).toHaveLength(1);
    expect(violations("Sem nota, ranking ou preço-alvo.")).toEqual([]);
    expect(violations("Pior mês: fevereiro de 2025.")).toEqual([]);
  });

  it("todo título de ordenação possível é neutro", () => {
    const fields = Object.keys(SORT_LABELS) as SortField[];
    const titles = fields.flatMap((field) => [
      sortTitle({ field, dir: "asc" }),
      sortTitle({ field, dir: "desc" }),
    ]);
    const presets = Object.values(SORT_PRESETS).flat().map(sortTitle);
    for (const title of [...titles, ...presets]) {
      expect(violations(`${title}.`), title).toEqual([]);
    }
  });

  it("títulos das classes e do menu são neutros", () => {
    const texts = [
      ...MARKET_CLASSES.flatMap((c) => [c.title, c.description, c.intro, c.label]),
      ...PORTAL_NAV.map((item) => item.label),
    ];
    for (const text of texts) {
      expect(violations(`${text}.`), text).toEqual([]);
    }
  });
});
