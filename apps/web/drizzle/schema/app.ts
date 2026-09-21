import { pgSchema } from "drizzle-orm/pg-core";

// Schema `app` (site.md §4.1, §4.2, §4.4). Arquivo próprio para evitar import circular com index.ts.
export const app = pgSchema("app");
