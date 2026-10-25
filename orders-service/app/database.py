import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.security_config import read_secret

load_dotenv()

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",      # залиште свій драйвер
    username=os.environ["POSTGRES_USER"],
    password=read_secret("db_password"),
    host=os.getenv("POSTGRES_HOST", "postgres"),
    port=5432,
    database=os.environ["POSTGRES_DB"],
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """Provide a database session for a request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
