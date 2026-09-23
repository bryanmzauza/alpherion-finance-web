import { describe, expect, it } from "vitest";
import {
  DEFAULT_SORT,
  SORT_PRESETS,
  SORTABLE_BY_CLASS,
  parseSort,
  sortPhrase,
  sortQuery,
  sortTitle,
} from "@/lib/market-sort";

describe("ordenação por URL", () => {
  it("campo fora da lista volta para o padrão neutro (liquidez)", () => {
    expect(parseSort({ sort: "potencial", dir: "desc" })).toEqual(DEFAULT_SORT);
    expect(parseSort({})).toEqual(DEFAULT_SORT);
    expect(DEFAULT_SORT).toEqual({ field: "volume", dir: "desc" });
  });

  it("campo que a classe não aceita também volta para o padrão", () => {
    expect(parseSort({ sort: "pe", dir: "asc" }, SORTABLE_BY_CLASS.etfs)).toEqual(DEFAULT_SORT);
  });

  it("direção inválida vira desc", () => {
    expect(parseSort({ sort: "dy_12m", dir: "x" })).toEqual({ field: "dy_12m", dir: "desc" });
  });

  it("padrão não põe parâmetro na URL (a página indexável não tem query)", () => {
    expect(sortQuery(DEFAULT_SORT)).toBe("");
    expect(sortQuery({ field: "pvp", dir: "asc" })).toBe("?sort=pvp&dir=asc");
  });
});

describe("título do preset", () => {
  it("diz a métrica e a direção, nada mais", () => {
    expect(sortTitle({ field: "dy_12m", dir: "desc" })).toBe("Maior dividend yield 12 m");
    expect(sortTitle({ field: "pvp", dir: "asc" })).toBe("Menor P/VP");
    expect(sortTitle({ field: "ticker", dir: "asc" })).toBe("Código de A a Z");
    expect(sortPhrase({ field: "volume", dir: "desc" })).toBe(
      "ordenados por volume financeiro do dia, do maior para o menor",
    );
  });

  it("todo preset usa campo aceito pela classe", () => {
    for (const [classe, presets] of Object.entries(SORT_PRESETS)) {
      for (const preset of presets) {
        expect(SORTABLE_BY_CLASS[classe]).toContain(preset.field);
      }
    }
  });

  it("não há preset de 'menor P/L' (prejuízo apareceria primeiro)", () => {
    const todos = Object.values(SORT_PRESETS).flat();
    expect(todos).not.toContainEqual({ field: "pe", dir: "asc" });
  });
});
