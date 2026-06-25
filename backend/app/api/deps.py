"""Reusable API dependencies — most importantly, "who is the current user?".

`get_current_user` is the gate that protects endpoints: it reads the Bearer
token, verifies the JWT, loads the user, and either returns them or raises 401.
Any route that wants "must be logged in" just declares `current_user: CurrentUser`.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.db.session import get_db
from app.models.user import User

# Tells FastAPI to look for `Authorization: Bearer <token>`. tokenUrl points at
# our login route so the /docs "Authorize" button knows where to get a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)         # verifies signature + expiry
        user_id = payload.get("sub")                 # we stored the user id in `sub`
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        # Forged, altered, or expired token -> treat as not-authenticated.
        raise credentials_exception

    user = user_crud.get_user_by_id(db, int(user_id))
    if user is None:
        raise credentials_exception
    return user


# A type alias so routes can write `current_user: CurrentUser` instead of the
# full `Annotated[...]` each time. Reads cleanly and is reusable.
CurrentUser = Annotated[User, Depends(get_current_user)]
