# Backend (FastAPI) production image.
# Builds a small Python image, installs deps, and on start runs DB migrations
# then launches the server. Used by Render (see render.yaml) or any Docker host.

FROM python:3.10-slim

# Don't buffer stdout/stderr (so logs show up immediately) and don't write .pyc.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first (their own layer) so code changes don't re-install everything.
# psycopg[binary] ships prebuilt, so we need no system build tools here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend app, alembic config, and migrations.
COPY . .

# On boot: apply any pending migrations, THEN serve. Render injects $PORT; default
# to 8000 locally. Running migrations here means a fresh DB is set up on first deploy.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
