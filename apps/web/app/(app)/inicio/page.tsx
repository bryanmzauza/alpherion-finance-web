import { redirect } from "next/navigation";
import { getPortfolio } from "@/lib/portfolio/repo";
import { requireSession } from "@/lib/session";

// `/` do app (o proxy reescreve para cá): quem já tem carteira vai para ela; quem não
// tem, para a criação (site.md §2.2).
export default async function InicioPage() {
  const session = await requireSession("/inicio");
  redirect((await getPortfolio(session.user.id)) ? "/carteira" : "/carteira/nova");
}
