-- O schema "app" é criado pelo infra/postgres/init.sql (dono: usuário web), nunca pela migration.
CREATE TYPE "app"."consent_kind" AS ENUM('terms', 'privacy', 'newsletter');--> statement-breakpoint
CREATE TYPE "app"."consent_source" AS ENUM('landing', 'app_signup', 'app_settings');--> statement-breakpoint
CREATE TYPE "app"."data_request_kind" AS ENUM('access', 'export', 'delete', 'correct', 'portability');--> statement-breakpoint
CREATE TYPE "app"."data_request_status" AS ENUM('open', 'in_progress', 'fulfilled', 'rejected');--> statement-breakpoint
CREATE TABLE "app"."consents" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"subscriber_email_hash" text,
	"kind" "app"."consent_kind" NOT NULL,
	"document_version" text NOT NULL,
	"accepted_at" timestamp with time zone DEFAULT now() NOT NULL,
	"ip" "inet",
	"user_agent" text,
	"source" "app"."consent_source" NOT NULL,
	"withdrawn_at" timestamp with time zone
);
--> statement-breakpoint
CREATE TABLE "app"."data_requests" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid,
	"email" text NOT NULL,
	"kind" "app"."data_request_kind" NOT NULL,
	"status" "app"."data_request_status" DEFAULT 'open' NOT NULL,
	"requested_at" timestamp with time zone DEFAULT now() NOT NULL,
	"fulfilled_at" timestamp with time zone,
	"notes" text
);
--> statement-breakpoint
CREATE INDEX "consents_subscriber_email_hash_idx" ON "app"."consents" USING btree ("subscriber_email_hash");--> statement-breakpoint
CREATE INDEX "consents_user_id_idx" ON "app"."consents" USING btree ("user_id");