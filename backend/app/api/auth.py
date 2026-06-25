"""Auth routes: signup, login, and "who am I".

An APIRouter is a mini-app you attach to the main FastAPI app. Grouping auth
routes here (prefix="/auth") keeps main.py tiny and the codebase organized.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.security import create_access_token, verify_password
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """Create a new account. Fails with 409 if the email is already taken."""
    if user_crud.get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = user_crud.create_user(db, email=payload.email, password=payload.password)
    return user  # FastAPI serializes it through UserRead (so no hash leaks out)


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    """Verify credentials and return a JWT.

    OAuth2PasswordRequestForm reads `username` + `password` as FORM fields (the
    OAuth2 "password flow" standard). We treat `username` as the email. Sending
    one vague "incorrect email or password" avoids leaking which one was wrong.
    """
    user = user_crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject=user.id))


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser):
    """Return the logged-in user. Protected: requires a valid Bearer token.

    There's no `logout` endpoint: a JWT is stateless, so "logging out" means the
    client simply deletes its stored token. (Server-side revocation would need a
    token blocklist — a later enhancement.)
    """
    return current_user
