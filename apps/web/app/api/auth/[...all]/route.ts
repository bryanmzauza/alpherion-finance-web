import { toNextJsHandler } from "better-auth/next-js";
import { auth } from "@/lib/auth";

// Endpoints do Better Auth (verificação do magic link, callback do Google, sign-out…).
// Só o host do app os expõe em produção (nginx, `20-app.conf`).
export const { GET, POST } = toNextJsHandler(auth);
