import type { EventKind, SecurityType } from "@/lib/market";

// Datas da `/agenda` (site.md §2.1, plano 4.3).
//
// A semana é a **ISO** (segunda a domingo, semana 1 = a que tem a primeira quinta do
// ano), e o caminho é `/agenda/2026-39` — o mesmo formato que o job `revalidate_pages`
// da API monta (`agenda_paths`). Se um mudar sem o outro, a revalidação passa a avisar
// páginas que não existem e a semana corrente fica velha em silêncio.
//
// Toda conta é em UTC sobre datas "puras" (YYYY-MM-DD): o dia de hoje é o de São
// Paulo, mas a aritmética de calendário não pode depender do fuso do servidor.

const DAY_MS = 86_400_000;

export const AGENDA_TIMEZONE = "America/Sao_Paulo";

/** Primeiro ano com agenda carregada; antes disso a página não existe (404). */
export const FIRST_YEAR = 2020;

/** Semanas mais antigas que isso saem do índice (`noindex`): agenda velha não é notícia. */
export const INDEX_WINDOW_DAYS = 365;

export type Week = { year: number; week: number };

/** Hoje em São Paulo, como `YYYY-MM-DD`. */
export function todayIso(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: AGENDA_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export function parseIso(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`);
}

export function toIso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(iso: string, days: number): string {
  return toIso(new Date(parseIso(iso).getTime() + days * DAY_MS));
}

/** Semana ISO de uma data. 31/12/2026 é a semana 53 de 2026; 01/01/2027, também. */
export function isoWeek(iso: string): Week {
  const date = parseIso(iso);
  const weekday = date.getUTCDay() || 7; // domingo = 7
  const thursday = new Date(date.getTime() + (4 - weekday) * DAY_MS);
  const year = thursday.getUTCFullYear();
  const jan1 = Date.UTC(year, 0, 1);
  const week = Math.floor((thursday.getTime() - jan1) / DAY_MS / 7) + 1;
  return { year, week };
}

/** Segunda-feira da semana ISO. */
export function weekStart({ year, week }: Week): string {
  const jan4 = Date.UTC(year, 0, 4);
  const jan4Weekday = new Date(jan4).getUTCDay() || 7;
  const firstMonday = jan4 - (jan4Weekday - 1) * DAY_MS;
  return toIso(new Date(firstMonday + (week - 1) * 7 * DAY_MS));
}

/** Os sete dias (segunda → domingo) da semana. */
export function weekDays(week: Week): string[] {
  const start = weekStart(week);
  return Array.from({ length: 7 }, (_, i) => addDays(start, i));
}

/** 52 ou 53: o ano ISO tem 53 semanas quando 28/12 cai na semana 53. */
export function weeksInYear(year: number): number {
  return isoWeek(`${year}-12-28`).week;
}

export function weekSlug({ year, week }: Week): string {
  return `${year}-${String(week).padStart(2, "0")}`;
}

export function weekPath(week: Week): string {
  return `/agenda/${weekSlug(week)}`;
}

export function shiftWeek(week: Week, delta: number): Week {
  return isoWeek(addDays(weekStart(week), delta * 7));
}

/**
 * `2026-39` → semana; qualquer outra coisa → `null` (a página responde 404).
 * O limite superior é o ano que vem: agenda de 2031 não tem fato ainda.
 */
export function parseWeekSlug(slug: string, today: string = todayIso()): Week | null {
  const match = /^(\d{4})-(\d{2})$/.exec(slug);
  if (!match) return null;
  const year = Number(match[1]);
  const week = Number(match[2]);
  const lastYear = parseIso(today).getUTCFullYear() + 1;
  if (year < FIRST_YEAR || year > lastYear) return null;
  if (week < 1 || week > weeksInYear(year)) return null;
  return { year, week };
}

// --- mês --------------------------------------------------------------------

export type Month = { year: number; month: number };

export function monthSlug({ year, month }: Month): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function monthPath(month: Month): string {
  return `/agenda/mes/${monthSlug(month)}`;
}

export function parseMonthSlug(slug: string, today: string = todayIso()): Month | null {
  const match = /^(\d{4})-(\d{2})$/.exec(slug);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const lastYear = parseIso(today).getUTCFullYear() + 1;
  if (year < FIRST_YEAR || year > lastYear || month < 1 || month > 12) return null;
  return { year, month };
}

export function monthOf(iso: string): Month {
  const date = parseIso(iso);
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1 };
}

export function shiftMonth({ year, month }: Month, delta: number): Month {
  const index = year * 12 + (month - 1) + delta;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

/**
 * Semanas (segunda → domingo) que cobrem o mês, para a grade mensal. O começo e o fim
 * da grade transbordam para os meses vizinhos, como em qualquer calendário de parede.
 */
export function monthGrid({ year, month }: Month): string[][] {
  const first = `${year}-${String(month).padStart(2, "0")}-01`;
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const last = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
  const weeks: string[][] = [];
  let cursor = weekStart(isoWeek(first));
  while (cursor <= last) {
    weeks.push(Array.from({ length: 7 }, (_, i) => addDays(cursor, i)));
    cursor = addDays(cursor, 7);
  }
  return weeks;
}

// --- filtros ----------------------------------------------------------------

/** Os três tipos do filtro da agenda (plano 4.3) e os `kind` da API que cada um reúne. */
export const EVENT_GROUPS = [
  { slug: "proventos", label: "Proventos", kinds: ["ex_date", "payment", "corporate"] },
  { slug: "comunicados", label: "Comunicados", kinds: ["document"] },
  { slug: "macro", label: "Macro", kinds: ["macro"] },
] as const satisfies readonly { slug: string; label: string; kinds: readonly EventKind[] }[];

export type EventGroup = (typeof EVENT_GROUPS)[number]["slug"];

export function groupOf(kind: EventKind): EventGroup {
  return EVENT_GROUPS.find((g) => (g.kinds as readonly EventKind[]).includes(kind))?.slug ?? "macro";
}

/** Classes do filtro. `macro` é a classe dos eventos que não são de papel nenhum. */
export const EVENT_CLASSES = [
  { slug: "acoes", label: "Ações", types: ["stock", "unit"] },
  { slug: "fiis", label: "FIIs", types: ["fii", "fiagro"] },
  { slug: "etfs", label: "ETFs", types: ["etf"] },
  { slug: "bdrs", label: "BDRs", types: ["bdr"] },
] as const satisfies readonly { slug: string; label: string; types: readonly SecurityType[] }[];

export type EventClass = (typeof EVENT_CLASSES)[number]["slug"] | "macro";

export function classOf(type: SecurityType | null): EventClass {
  if (type === null) return "macro";
  return (
    EVENT_CLASSES.find((c) => (c.types as readonly SecurityType[]).includes(type))?.slug ?? "macro"
  );
}

/**
 * "Comunicados relevantes" (§2.1) é a categoria **da CVM**, não um critério nosso:
 * a agenda do mercado inteiro lista só Fato Relevante. Os demais comunicados de cada
 * empresa ficam na página do ativo.
 */
export const AGENDA_DOCUMENT_CATEGORIES = ["Fato Relevante"];

/** Lê `?tipo=proventos,macro` / `?classe=fiis` — valor fora da lista é ignorado. */
export function parseFilter<T extends string>(raw: string | null, allowed: readonly T[]): T[] {
  if (!raw) return [];
  const wanted = new Set(raw.split(",").map((s) => s.trim()));
  return allowed.filter((value) => wanted.has(value));
}
