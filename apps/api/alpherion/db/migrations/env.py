"""Ambiente do Alembic para o schema `market`.

Roda com o usuário `data` (DATA_DATABASE_URL): é ele quem escreve em `market`.
A tabela `alembic_version` fica dentro do próprio schema.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from alpherion.db.base import SCHEMA, Base
from alpherion.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# configparser trata % como interpolação: escapar (a URL tem %20 e %3D no search_path).
config.set_main_option("sqlalchemy.url", get_settings().data_database_url.replace("%", "%%"))
target_metadata = Base.metadata


def include_object(obj: object, name: str | None, type_: str, *_: object) -> bool:
    # Só o schema market: nunca gerar diff para tabelas do `app` (Drizzle) ou do `public`.
    if type_ == "table":
        return getattr(obj, "schema", None) == SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
