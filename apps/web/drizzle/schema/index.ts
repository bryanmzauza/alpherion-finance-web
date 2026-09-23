// As tabelas entram por etapa: consents/data_requests (2.3), auth e audit_log (5.0),
// carteira (5.1), analyses (6).
export { app } from "./app";
export * from "./audit-log";
export * from "./auth";
export * from "./consents";
export * from "./data-requests";
export * from "./portfolio";
