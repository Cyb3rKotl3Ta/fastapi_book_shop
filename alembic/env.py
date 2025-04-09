from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Get the Alembic configuration object which provides access to the .ini file.
config = context.config

# Override the SQLAlchemy URL if needed.
config.set_main_option("sqlalchemy.url", "postgresql://user:password@localhost:5434/bookshop_db")

# Set up logging from the config file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the Base from your application. This Base is defined in your async engine code,
# but we only need its metadata for migrations.
from app.db.base import Base  # Ensure that this path is correct.

# import app.db.models.book
# import app.db.models.purchase
# import app.db.models.user
# import app.db.models.association_tables

import pkgutil
import importlib

models_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'app', 'db', 'models')
for finder, name, ispkg in pkgutil.iter_modules([models_path]):
    # Optionally, you can filter names if you only want certain files
    importlib.import_module(f"app.db.models.{name}")
    
    # Debug print: List all registered tables
print("Registered tables:", list(Base.metadata.tables.keys()))

# Now Alembic knows all the tables from these models
target_metadata = Base.metadata 
# import os
# import sys
# import pkgutil
# import importlib

# # Add the project root to sys.path so that the db_models directory can be found
# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname('models'), '..')))

# # Import the Base from your base module
# from app.db.base import Base

# # Automatically import all Python modules in the db_models directory
# db_models_path = os.path.join(os.path.dirname(__file__), '..', 'models')
# for module_info in pkgutil.iter_modules([db_models_path]):
#     module_name = module_info.name
#     # Optionally, skip modules that you don't want to import (e.g., __init__.py or utilities)
#     if module_name == "base":
#         continue
#     importlib.import_module(f"models.{module_name}")

# Set target_metadata to your Base.metadata so Alembic knows about all models
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    It is useful for generating SQL scripts without needing a live DB connection.
    """
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
    """
    Run migrations in 'online' mode.

    In this mode, a synchronous Engine is created and a connection is associated with the context.
    This allows Alembic to execute the migration operations on the live database.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# import asyncio
# from sqlalchemy.ext.asyncio import create_async_engine
# from sqlalchemy.pool import NullPool

# def do_run_migrations(connection):
#     # This function remains synchronous.
#     context.configure(
#         connection=connection,
#         target_metadata=target_metadata
#     )
#     with context.begin_transaction():
#         context.run_migrations()

# async def run_async_migrations_online() -> None:
#     """
#     Run migrations in 'online' mode using an asynchronous engine.
#     """
#     # Create an async engine; make sure your config contains the async URL
#     connectable = create_async_engine(
#         config.get_section(config.config_ini_section, {}),
#         prefix="sqlalchemy.",
#         poolclass=NullPool,
#     )

#     async with connectable.connect() as connection:
#         # Run the synchronous migration function in the async context
#         await connection.run_sync(do_run_migrations)

#     await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    # asyncio.run(run_async_migrations_online())
    run_migrations_online()
