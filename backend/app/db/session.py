"""Database engine, session factory, and the FastAPI `get_db` dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The Engine manages a POOL of connections to Postgres. Create it once; reuse it
# for the whole app. `pool_pre_ping` quietly checks a pooled connection is still
# alive before handing it out (avoids "server closed the connection" errors).
engine = create_engine(
    settings.database_url,
    echo=False,            # flip to True to print every SQL statement (handy for learning)
    pool_pre_ping=True,
)

# A factory that creates new Session objects bound to our engine.
#   autoflush=False   -> we control when pending changes are sent to the DB
#   autocommit=False  -> changes aren't saved until we explicitly commit()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and always closes it.

    The `yield` hands the session to the route function; once the response is
    sent, control returns here and the `finally` block closes the session,
    returning its connection to the pool — even if the route raised an error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
