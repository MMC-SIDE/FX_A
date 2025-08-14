from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# プロジェクトのルートディレクトリを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """データベースURLを取得"""
    # 環境変数から取得（本番環境）
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # 設定ファイルから取得（開発環境）
    try:
        import configparser
        db_config = configparser.ConfigParser()
        db_config.read('config/database.conf', encoding='utf-8')
        
        host = db_config.get('database', 'host', fallback='localhost')
        port = db_config.getint('database', 'port', fallback=5432)
        database = db_config.get('database', 'database', fallback='fx_trading')
        username = db_config.get('database', 'username', fallback='fx_user')
        password = db_config.get('database', 'password', fallback='fx_password')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    except:
        # フォールバック（alembic.iniから取得）
        return config.get_main_option("sqlalchemy.url")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_url()
    
    connectable = engine_from_config(
        configuration,
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