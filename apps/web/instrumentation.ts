// Roda uma vez no boot do servidor (Node). Importar `env` aqui faz o processo
// falhar cedo se faltar variável, em vez de quebrar na primeira request.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("@/lib/env");
  }
}
