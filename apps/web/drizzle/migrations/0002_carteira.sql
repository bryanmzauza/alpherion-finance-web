CREATE TYPE "app"."asset_class" AS ENUM('crypto', 'stablecoin', 'stock_br', 'bdr', 'etf_br', 'fii', 'fixed_income', 'treasury', 'other');--> statement-breakpoint
CREATE TYPE "app"."entry_source" AS ENUM('manual', 'csv', 'b3_import', 'b3_api');--> statement-breakpoint
CREATE TYPE "app"."import_source" AS ENUM('csv', 'b3_posicao', 'b3_negociacao', 'b3_proventos');--> statement-breakpoint
CREATE TYPE "app"."import_status" AS ENUM('imported', 'failed');--> statement-breakpoint
CREATE TYPE "app"."income_kind" AS ENUM('dividend', 'jcp', 'fii_income', 'interest', 'other');--> statement-breakpoint
CREATE TYPE "app"."market_ref" AS ENUM('ticker', 'coingecko_id', 'treasury_slug', 'none');--> statement-breakpoint
CREATE TYPE "app"."transaction_side" AS ENUM('buy', 'sell');--> statement-breakpoint
CREATE TABLE "app"."assets" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"symbol" text NOT NULL,
	"name" text NOT NULL,
	"asset_class" "app"."asset_class" NOT NULL,
	"market_ref" "app"."market_ref" DEFAULT 'ticker' NOT NULL,
	"currency" text DEFAULT 'BRL' NOT NULL,
	"factor_map" jsonb,
	"active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."import_batches" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"portfolio_id" uuid NOT NULL,
	"source" "app"."import_source" NOT NULL,
	"file_sha256" text NOT NULL,
	"rows_in" integer NOT NULL,
	"rows_imported" integer NOT NULL,
	"rows_skipped" integer NOT NULL,
	"warnings" jsonb,
	"status" "app"."import_status" NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."income_events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"portfolio_id" uuid NOT NULL,
	"asset_id" uuid NOT NULL,
	"date" date NOT NULL,
	"kind" "app"."income_kind" NOT NULL,
	"payload" text NOT NULL,
	"key_version" smallint NOT NULL,
	"source" "app"."entry_source" NOT NULL,
	"import_batch_id" uuid,
	"external_key" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."portfolios" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"name" text NOT NULL,
	"base_currency" text DEFAULT 'BRL' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."position_adjustments" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"portfolio_id" uuid NOT NULL,
	"asset_id" uuid NOT NULL,
	"payload" text NOT NULL,
	"key_version" smallint NOT NULL,
	"source" "app"."entry_source" DEFAULT 'manual' NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "app"."transactions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"portfolio_id" uuid NOT NULL,
	"asset_id" uuid NOT NULL,
	"date" date NOT NULL,
	"side" "app"."transaction_side" NOT NULL,
	"payload" text NOT NULL,
	"key_version" smallint NOT NULL,
	"source" "app"."entry_source" NOT NULL,
	"import_batch_id" uuid,
	"external_key" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "app"."import_batches" ADD CONSTRAINT "import_batches_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "app"."users"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."import_batches" ADD CONSTRAINT "import_batches_portfolio_id_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "app"."portfolios"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."income_events" ADD CONSTRAINT "income_events_portfolio_id_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "app"."portfolios"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."income_events" ADD CONSTRAINT "income_events_asset_id_assets_id_fk" FOREIGN KEY ("asset_id") REFERENCES "app"."assets"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."income_events" ADD CONSTRAINT "income_events_import_batch_id_import_batches_id_fk" FOREIGN KEY ("import_batch_id") REFERENCES "app"."import_batches"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."portfolios" ADD CONSTRAINT "portfolios_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "app"."users"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."position_adjustments" ADD CONSTRAINT "position_adjustments_portfolio_id_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "app"."portfolios"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."position_adjustments" ADD CONSTRAINT "position_adjustments_asset_id_assets_id_fk" FOREIGN KEY ("asset_id") REFERENCES "app"."assets"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."transactions" ADD CONSTRAINT "transactions_portfolio_id_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "app"."portfolios"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."transactions" ADD CONSTRAINT "transactions_asset_id_assets_id_fk" FOREIGN KEY ("asset_id") REFERENCES "app"."assets"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "app"."transactions" ADD CONSTRAINT "transactions_import_batch_id_import_batches_id_fk" FOREIGN KEY ("import_batch_id") REFERENCES "app"."import_batches"("id") ON DELETE set null ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "assets_class_symbol_idx" ON "app"."assets" USING btree ("asset_class","symbol");--> statement-breakpoint
CREATE INDEX "import_batches_user_id_idx" ON "app"."import_batches" USING btree ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "import_batches_portfolio_file_idx" ON "app"."import_batches" USING btree ("portfolio_id","file_sha256");--> statement-breakpoint
CREATE INDEX "income_events_portfolio_date_idx" ON "app"."income_events" USING btree ("portfolio_id","date");--> statement-breakpoint
CREATE UNIQUE INDEX "income_events_portfolio_external_key_idx" ON "app"."income_events" USING btree ("portfolio_id","external_key");--> statement-breakpoint
CREATE INDEX "portfolios_user_id_idx" ON "app"."portfolios" USING btree ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "position_adjustments_portfolio_asset_idx" ON "app"."position_adjustments" USING btree ("portfolio_id","asset_id");--> statement-breakpoint
CREATE INDEX "transactions_portfolio_date_idx" ON "app"."transactions" USING btree ("portfolio_id","date");--> statement-breakpoint
CREATE UNIQUE INDEX "transactions_portfolio_external_key_idx" ON "app"."transactions" USING btree ("portfolio_id","external_key");