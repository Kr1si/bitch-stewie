"""Sync SQLAlchemy engine for worker threads and the CLI.

The cc_bridge runs on a Proactor event loop (asyncio subprocess support), where
async psycopg cannot operate on Windows - so bridge/CLI persistence goes
through this sync engine instead.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from assistant.config import get_settings

_engine = None
_factory: sessionmaker[Session] | None = None


def get_sync_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        _engine = create_engine(url, pool_size=3)
    return _engine


def get_sync_session_factory() -> sessionmaker[Session]:
    global _factory
    if _factory is None:
        _factory = sessionmaker(get_sync_engine(), expire_on_commit=False)
    return _factory
