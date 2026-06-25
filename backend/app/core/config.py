"""Application configuration.

Settings are loaded from environment variables (and the repo-root ".env" file)
using pydantic-settings. Reading config from the environment — instead of
hard-coding it — is the "12-factor" approach: the same code runs locally, in
CI, and in production just by changing env vars.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the repo-root ".env", computed from THIS file's location so
# it works no matter which directory you launch uvicorn from.
#   config.py -> core -> app -> backend -> <repo root>
#   parents[0]  [1]     [2]    [3]
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # Each attribute is matched (case-insensitively) to an env var of the same
    # name, e.g. `postgres_user` <- POSTGRES_USER.
    #
    # Local dev sets the POSTGRES_* parts (from the repo .env). In production a
    # managed host (e.g. Render) instead gives ONE connection string — so these
    # are optional, and DATABASE_URL_OVERRIDE (below) takes precedence when set.
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Full DB URL from a managed host. When set, it wins over the POSTGRES_* parts.
    # (Render's "connectionString" is wired into this via render.yaml.)
    database_url_override: str | None = None

    # --- CORS (which browser origins may call this API) ---
    # Comma-separated exact origins (local dev defaults below)...
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # ...plus an optional regex so we can allow e.g. any *.onrender.com frontend
    # without hard-coding the deploy URL. Unset locally.
    allowed_origin_regex: str | None = None

    # --- Auth / JWT ---
    # secret_key has NO default on purpose: the app must not start without one.
    secret_key: str
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # --- Optional LLM summarizer ---
    # Leave ANTHROPIC_API_KEY unset to disable the "Summarize board" feature.
    anthropic_api_key: str | None = None
    summarizer_model: str = "claude-opus-4-8"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",  # don't error on unrelated keys in .env
    )

    @property
    def database_url(self) -> str:
        """SQLAlchemy connection URL.

        `postgresql+psycopg://` selects the psycopg (v3) driver, which speaks
        BOTH sync and async — so switching to async later won't require swapping
        the driver.
        """
        if self.database_url_override:
            url = self.database_url_override
            # Managed hosts hand out "postgres://" or "postgresql://"; normalize
            # the scheme to the psycopg v3 driver our engine expects.
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> list[str]:
        """The comma-separated `allowed_origins` as a clean list of exact origins.
        A bare host (no scheme) is assumed https (so a `fromService` host works)."""
        origins: list[str] = []
        for raw in self.allowed_origins.split(","):
            o = raw.strip()
            if not o:
                continue
            if not o.startswith(("http://", "https://")):
                o = f"https://{o}"
            origins.append(o)
        return origins


# A single, importable settings instance used across the app.
settings = Settings()
