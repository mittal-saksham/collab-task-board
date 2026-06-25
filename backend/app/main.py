"""FastAPI application entrypoint.

Run it (from the `backend/` directory, with the virtualenv active):
    uvicorn app.main:app --reload
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import auth
from app.db.session import get_db

app = FastAPI(title="Collab Task Board API")

# Attach the auth routes (/auth/signup, /auth/login, /auth/me).
app.include_router(auth.router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Liveness + database connectivity check.

    `Depends(get_db)` injects a Session. We run a trivial `SELECT 1` so a green
    response *proves* the backend can actually reach Postgres — not just that
    the web server is up.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
