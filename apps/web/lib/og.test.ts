import { describe, expect, it } from "vitest";
import { splitGold } from "./og";

describe("splitGold", () => {
  it("separa a palavra dourada na primeira ocorrência, sem diferenciar maiúsculas", () => {
    expect(splitGold("Você sabe o que tem?", "tem")).toEqual(["Você sabe o que ", "tem", "?"]);
    expect(splitGold("O que é o raio-x de carteira", "RAIO-X")).toEqual(["O que é o ", "raio-x", " de carteira"]);
  });

  it("mantém o título inteiro quando a palavra não aparece", () => {
    expect(splitGold("Sobre", "tese")).toEqual(["Sobre", "", ""]);
  });
});
