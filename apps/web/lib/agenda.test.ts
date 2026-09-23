import { describe, expect, it } from "vitest";
import {
  classOf,
  groupOf,
  isoWeek,
  monthGrid,
  parseFilter,
  parseMonthSlug,
  parseWeekSlug,
  shiftMonth,
  shiftWeek,
  todayIso,
  weekDays,
  weekPath,
  weekStart,
  weeksInYear,
} from "@/lib/agenda";

describe("semana ISO", () => {
  it("23/09/2026 é a semana 39, de segunda 21 a domingo 27", () => {
    expect(isoWeek("2026-09-23")).toEqual({ year: 2026, week: 39 });
    expect(weekDays({ year: 2026, week: 39 })).toEqual([
      "2026-09-21",
      "2026-09-22",
      "2026-09-23",
      "2026-09-24",
      "2026-09-25",
      "2026-09-26",
      "2026-09-27",
    ]);
  });

  it("na virada do ano vale o ano ISO, não o do calendário", () => {
    expect(isoWeek("2026-12-31")).toEqual({ year: 2026, week: 53 });
    expect(isoWeek("2027-01-03")).toEqual({ year: 2026, week: 53 });
    expect(isoWeek("2027-01-04")).toEqual({ year: 2027, week: 1 });
    expect(isoWeek("2021-01-01")).toEqual({ year: 2020, week: 53 });
  });

  it("2026 tem 53 semanas; 2027, 52", () => {
    expect(weeksInYear(2026)).toBe(53);
    expect(weeksInYear(2027)).toBe(52);
  });

  it("segunda-feira da semana 1 pode cair no ano anterior", () => {
    expect(weekStart({ year: 2026, week: 1 })).toBe("2025-12-29");
  });

  it("anda de semana atravessando o ano", () => {
    expect(shiftWeek({ year: 2026, week: 53 }, 1)).toEqual({ year: 2027, week: 1 });
    expect(shiftWeek({ year: 2027, week: 1 }, -1)).toEqual({ year: 2026, week: 53 });
  });

  it("caminho no mesmo formato do job revalidate_pages da API", () => {
    // apps/api/tests/test_portal_etapa4.py prende o mesmo formato do outro lado.
    expect(weekPath(isoWeek("2026-09-23"))).toBe("/agenda/2026-39");
    expect(weekPath({ year: 2027, week: 1 })).toBe("/agenda/2027-01");
  });
});

describe("parâmetros da URL", () => {
  const hoje = "2026-09-23";

  it("aceita só semana que existe", () => {
    expect(parseWeekSlug("2026-39", hoje)).toEqual({ year: 2026, week: 39 });
    expect(parseWeekSlug("2026-53", hoje)).toEqual({ year: 2026, week: 53 });
    expect(parseWeekSlug("2027-53", hoje)).toBeNull();
    expect(parseWeekSlug("2026-00", hoje)).toBeNull();
    expect(parseWeekSlug("2026-9", hoje)).toBeNull();
    expect(parseWeekSlug("abc", hoje)).toBeNull();
  });

  it("não abre agenda de antes da carga nem de daqui a dois anos", () => {
    expect(parseWeekSlug("2019-10", hoje)).toBeNull();
    expect(parseWeekSlug("2027-10", hoje)).not.toBeNull();
    expect(parseWeekSlug("2028-10", hoje)).toBeNull();
  });

  it("mês", () => {
    expect(parseMonthSlug("2026-10", hoje)).toEqual({ year: 2026, month: 10 });
    expect(parseMonthSlug("2026-13", hoje)).toBeNull();
    expect(shiftMonth({ year: 2026, month: 12 }, 1)).toEqual({ year: 2027, month: 1 });
    expect(shiftMonth({ year: 2026, month: 1 }, -1)).toEqual({ year: 2025, month: 12 });
  });

  it("filtro ignora valor fora da lista", () => {
    expect(parseFilter("proventos,macro,palpite", ["proventos", "comunicados", "macro"])).toEqual([
      "proventos",
      "macro",
    ]);
    expect(parseFilter(null, ["a"])).toEqual([]);
  });
});

describe("grade mensal", () => {
  it("outubro de 2026 começa na segunda 28/09 e cobre 5 semanas", () => {
    const grade = monthGrid({ year: 2026, month: 10 });
    expect(grade[0][0]).toBe("2026-09-28");
    expect(grade.at(-1)?.at(-1)).toBe("2026-11-01");
    expect(grade).toHaveLength(5);
  });
});

describe("classificação dos eventos", () => {
  it("data-com e pagamento são proventos", () => {
    expect(groupOf("ex_date")).toBe("proventos");
    expect(groupOf("payment")).toBe("proventos");
    expect(groupOf("document")).toBe("comunicados");
    expect(groupOf("macro")).toBe("macro");
  });

  it("unit é ação e fiagro é FII, como nas páginas", () => {
    expect(classOf("unit")).toBe("acoes");
    expect(classOf("fiagro")).toBe("fiis");
    expect(classOf(null)).toBe("macro");
  });
});

describe("hoje", () => {
  it("é o dia de São Paulo, não o do servidor", () => {
    // 02:00 UTC de 24/09 ainda é 23/09 em São Paulo.
    expect(todayIso(new Date("2026-09-24T02:00:00Z"))).toBe("2026-09-23");
  });
});
