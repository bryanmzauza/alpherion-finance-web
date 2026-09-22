-- Usuários por serviço e schemas (site.md §7.6). Executado por init.sh com variáveis psql.
--   web  → dono do schema app (Drizzle)
--   api  → SELECT no schema market; nada no app; statement_timeout 5 s (§7.5)
--   data → escrita no schema market (worker + Alembic); nada no app
-- O schema public fica sem CREATE para os três.

-- Extensões usadas pela busca de ativos (`/v1/assets/search`): pg_trgm para busca por
-- trecho do nome e unaccent para ignorar acento. Criadas pelo superusuário porque
-- CREATE EXTENSION exige privilégio que os usuários de serviço não têm (§7.6).
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE ROLE :"web_user"  LOGIN PASSWORD :'web_password';
CREATE ROLE :"api_user"  LOGIN PASSWORD :'api_password';
CREATE ROLE :"data_user" LOGIN PASSWORD :'data_password';

CREATE SCHEMA app    AUTHORIZATION :"web_user";
CREATE SCHEMA market AUTHORIZATION :"data_user";

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"DBNAME" TO :"web_user", :"api_user", :"data_user";
-- O migrator do Drizzle roda CREATE SCHEMA IF NOT EXISTS "app" antes de cada migration,
-- e o Postgres checa CREATE no banco antes do IF NOT EXISTS. Só o web recebe esse direito.
GRANT CREATE ON DATABASE :"DBNAME" TO :"web_user";

-- api: só leitura em market, inclusive nas tabelas que o data criar depois.
GRANT USAGE ON SCHEMA market TO :"api_user";
GRANT SELECT ON ALL TABLES IN SCHEMA market TO :"api_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"data_user" IN SCHEMA market GRANT SELECT ON TABLES TO :"api_user";
ALTER ROLE :"api_user" SET statement_timeout = '5s';

ALTER ROLE :"web_user"  SET search_path = app;
ALTER ROLE :"api_user"  SET search_path = market;
ALTER ROLE :"data_user" SET search_path = market;

-- Bancos próprios (§7.6): listmonk e umami não tocam o banco da aplicação.
CREATE ROLE listmonk LOGIN PASSWORD :'listmonk_password';
CREATE ROLE umami    LOGIN PASSWORD :'umami_password';
CREATE DATABASE listmonk OWNER listmonk;
CREATE DATABASE umami    OWNER umami;
REVOKE ALL ON DATABASE listmonk FROM PUBLIC;
REVOKE ALL ON DATABASE umami    FROM PUBLIC;
