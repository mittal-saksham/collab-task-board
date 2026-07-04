"""Auth routes: signup, login, and "who am I".

An APIRouter is a mini-app you attach to the main FastAPI app. Grouping auth
routes here (prefix="/auth") keeps main.py tiny and the codebase organized.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.ratelimit import login_limiter, signup_limiter
from app.core.security import create_access_token, dummy_verify, verify_password
from app.crud import user as user_crud
from app.db.session import get_db
from app.schemas.token import Token, WsTicket
from app.schemas.user import UserCreate, UserRead
from app.ws import tickets

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(signup_limiter)],
)
def signup(payload: UserCreate, db: Annotated[Session, Depends(get_db)]):
    """Create a new account. Fails with 409 if the email is already taken."""
    if user_crud.get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    user = user_crud.create_user(db, email=payload.email, password=payload.password)
    return user  # FastAPI serializes it through UserRead (so no hash leaks out)


@router.post("/login", response_model=Token, dependencies=[Depends(login_limiter)])
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    """Verify credentials and return a JWT.

    OAuth2PasswordRequestForm reads `username` + `password` as FORM fields (the
    OAuth2 "password flow" standard). We treat `username` as the email. Sending
    one vague "incorrect email or password" avoids leaking which one was wrong —
    and `dummy_verify` burns the same bcrypt cost on the unknown-email path, so
    the response TIME doesn't leak it either.
    """
    user = user_crud.get_user_by_email(db, form_data.username)
    if user is None:
        dummy_verify(form_data.password)  # equalize timing (see core/security.py)
        valid = False
    else:
        valid = verify_password(form_data.password, user.hashed_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(subject=user.id))


@router.post("/ws-ticket", response_model=WsTicket)
def create_ws_ticket(current_user: CurrentUser):
    """Mint a single-use, ~60s ticket for opening a board WebSocket.

    The WS handshake can't carry an Authorization header, so the client fetches
    one of these (over normal authenticated HTTPS) right before connecting and
    passes it as `?ticket=`. Unlike the JWT, a ticket in an access log is
    worthless: single-use, already burned, expires in a minute, no REST access.
    """
    return WsTicket(ticket=tickets.issue(current_user.id))


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser):
    """Return the logged-in user. Protected: requires a valid Bearer token.

    There's no `logout` endpoint: a JWT is stateless, so "logging out" means the
    client simply deletes its stored token. (Server-side revocation would need a
    token blocklist — a later enhancement.)
    """
    return current_user
