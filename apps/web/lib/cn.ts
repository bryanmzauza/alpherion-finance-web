// Junta classes ignorando falsy. Sem tailwind-merge: as classes aqui não conflitam por convenção.
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
