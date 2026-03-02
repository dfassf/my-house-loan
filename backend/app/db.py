from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_database_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_database_url(settings.database_url)
engine = (
    create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    if DATABASE_URL
    else None
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_db() -> Generator[Session]:
    if engine is None:
        raise RuntimeError("database_url이 설정되지 않았습니다.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
