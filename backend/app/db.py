from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        url = get_settings().database_url
        # prepare_threshold=None: no server-side prepared statements, which
        # transaction-mode poolers (Neon's -pooler endpoint) may not support.
        connect_args = ({"connect_timeout": 10, "prepare_threshold": None}
                        if url.startswith("postgresql") else {})
        _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a database session."""
    get_engine()
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
