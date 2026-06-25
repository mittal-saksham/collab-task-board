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
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # --- Auth / JWT ---
    # secret_key has NO default on purpose: the app must not start without one.
    secret_key: str
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

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
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# A single, importable settings instance used across the app.
settings = Settings()
