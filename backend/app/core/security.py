"""Security helpers: password hashing (bcrypt) and JWT creation/decoding.

Two independent concerns live here:
  1. Passwords  -> we store a one-way *hash*, never the plaintext.
  2. Tokens     -> after login we issue a signed JWT the client sends back.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


# --- Passwords ---------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt.

    `gensalt()` creates a new random salt each time, so two users with the same
    password get different hashes (defeats rainbow-table attacks). The salt is
    stored *inside* the resulting hash string, so we don't track it separately.

    NOTE: bcrypt only uses the first 72 bytes of the password — fine for normal
    use; just don't rely on bytes beyond that.
    """
    pwd_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash.

    bcrypt re-derives the hash using the salt embedded in `hashed_password`
    and compares — so we never need to decrypt anything (hashing is one-way).
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# --- JWT (JSON Web Token) ----------------------------------------------------

def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Create a signed JWT whose `sub` (subject) claim is the user's id.

    A JWT is three base64 parts: header.payload.signature. The signature is made
    with our SECRET_KEY, so the server can later verify the token wasn't tampered
    with — WITHOUT storing any session in the database (it's "stateless").
    """
    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": str(subject), "exp": expire}  # `exp` = expiry; jwt enforces it
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify a JWT's signature + expiry and return its payload.

    Raises jwt.PyJWTError (e.g. ExpiredSignatureError, InvalidTokenError) if the
    token is forged, altered, or expired — the caller turns that into a 401.
    """
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
