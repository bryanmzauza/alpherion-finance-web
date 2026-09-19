import { pgSchema } from "drizzle-orm/pg-core";

// Schema `app` (site.md §4.1, §4.2, §4.4). As tabelas entram por etapa:
// consents/data_requests (2.3), auth (4.0), carteira (4.1), analyses (5.4).
export const app = pgSchema("app");
