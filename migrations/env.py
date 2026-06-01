"""Alembic migration environment.

Resolves the database URL from the DATABASE_URL environment variable (loaded
from .env) so migrations target the same database as the application. The
project uses raw SQL rather than ORM models, so there is no target_metadata and
autogenerate is not used — migrations are written explicitly.
"""

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv()

config = context.config

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/ohio_credit"
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

# IMPORTANT: MLflow uses this same PostgreSQL database as its backend store and
# manages its own schema with Alembic in the default "alembic_version" table.
# We keep our application migrations in a dedicated version table so the two
# migration histories never collide.
VERSION_TABLE = "ohio_alembic_version"


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
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
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
