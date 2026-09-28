import os
from pathlib import Path
from alembic import context
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
url = os.environ['DATABASE_URL'].replace('postgresql://', 'postgresql+psycopg://', 1)
if context.is_offline_mode():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url).connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
