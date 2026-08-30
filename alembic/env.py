from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement .env
load_dotenv()

# Ajouter le répertoire racine au PYTHONPATH pour trouver database.py et models.py
sys.path.append(os.getcwd())

from database import Base, SQLALCHEMY_DATABASE_URL
import models  # Assure l'enregistrement des modèles SQLAlchemy pour autogenerate

config = context.config

# Injecter l'URL dynamique si elle est définie en échappant les symboles %
if SQLALCHEMY_DATABASE_URL:
    escaped_url = SQLALCHEMY_DATABASE_URL.replace("%", "%%")
    config.set_main_option("sqlalchemy.url", escaped_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()