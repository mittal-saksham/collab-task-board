# 🔐 Authentication (Signup, Login, JWT)

How a user proves who they are, and how protected endpoints check it. This is
another of your "hard parts" — by the end you should be able to trace a token
from issue → storage → request → validation.

---

## The big picture

```
SIGNUP                                  LOGIN
──────                                  ─────
client sends email + password           client sends email + password (form)
        │                                       │
        ▼                                       ▼
bcrypt-hash the password                verify password vs stored hash
        │                                       │
        ▼                                       ▼
INSERT user (hash, never plaintext)     create & return a signed JWT
        │                                       │
        ▼                                       ▼
201 + user (no password field)          200 + { access_token, token_type }

ACCESSING A PROTECTED ROUTE  (e.g. GET /auth/me)
────────────────────────────────────────────────
client sends:  Authorization: Bearer <token>
        │
        ▼
get_current_user dependency:
   decode + verify JWT signature & expiry  ──(bad/expired)──► 401
        │ (ok)
        ▼
   load User by id from the token's `sub`
        │
        ▼
   route runs with the authenticated user
```

---

## Part 1 — Passwords are hashed, never stored

> 🧠 **Hashing vs encryption:** encryption is reversible (you can decrypt);
> **hashing is one-way** (you can't un-hash). We hash passwords so that even if
> the database leaks, attackers don't get usable passwords.

We use **bcrypt** (`app/core/security.py`):

```python
def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain, hashed) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

- **`gensalt()`** generates a random **salt** per password. The salt makes two
  identical passwords hash to *different* strings, defeating precomputed
  "rainbow table" attacks. The salt is stored *inside* the hash, so we don't
  manage it separately.
- A stored hash looks like `$2b$12$....`:
  - `2b` = bcrypt version, `12` = "cost" (work factor — higher = slower = harder
    to brute-force).
- **Verifying** never decrypts: bcrypt re-hashes the input using the salt baked
  into the stored hash and compares.
- ⚠️ bcrypt only considers the first **72 bytes** of a password.

We confirmed in the DB that the stored value is `$2b$12$iwIX...` — a hash, not
the plaintext.

---

## Part 2 — Login issues a JWT

> 🧠 **JWT (JSON Web Token):** a compact, signed token of the form
> `header.payload.signature` (three base64url parts). The server signs it with a
> secret; anyone can *read* the payload, but only the server can *forge or alter*
> it. Because the signature proves authenticity, the server doesn't need to store
> sessions — it's **stateless**.

Our token (`create_access_token` in `security.py`):
```python
payload = {"sub": str(user.id), "exp": <now + 60 min>}
jwt.encode(payload, settings.secret_key, algorithm="HS256")
```
- **`sub`** ("subject") = the user's id. That's how we know *who* the token is
  for when it comes back.
- **`exp`** = expiry timestamp. PyJWT automatically rejects expired tokens on
  decode.
- **HS256** = HMAC-SHA256, a symmetric algorithm: the *same* `SECRET_KEY` signs
  and verifies. (That's why the secret must stay secret and out of git.)

### Why the login route uses a *form*, not JSON
`POST /auth/login` takes `OAuth2PasswordRequestForm` — `username` + `password`
as **form fields** (we treat `username` as the email). This follows the OAuth2
"password flow" standard, which gives us a bonus: the **`/docs` "Authorize"
button** works out of the box, so you can try protected endpoints right in the
browser. (`python-multipart` is the dependency that lets FastAPI parse form
data.)

---

## Part 3 — Protecting routes with a dependency

`get_current_user` (`app/api/deps.py`) is the reusable gate:

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token = Depends(oauth2_scheme), db = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)     # verifies signature + expiry
        user_id = payload["sub"]
    except jwt.PyJWTError:
        raise 401
    user = get_user_by_id(db, int(user_id))
    if not user: raise 401
    return user
```

- `OAuth2PasswordBearer` tells FastAPI to pull the token from the
  `Authorization: Bearer <token>` header (and documents the scheme in `/docs`).
- Any endpoint that needs auth just declares it:
  ```python
  @router.get("/me")
  def read_me(current_user: CurrentUser):   # CurrentUser = Annotated[User, Depends(get_current_user)]
      return current_user
  ```
- We verified: no token / bad token → **401**; valid token → **200** + the user.

---

## Part 4 — Where the frontend will store the token (our choice)

When we build the React app, after login we'll save the `access_token` in
**`localStorage`** and attach it to each request:
```ts
headers: { Authorization: `Bearer ${token}` }
```

**Why localStorage:** simplest, and it pairs cleanly with WebSocket auth later.

**The tradeoff (be ready to say this in an interview):** localStorage is readable
by any JavaScript on the page, so it's vulnerable to **XSS** (cross-site
scripting) — if an attacker injects a script, they can steal the token. The more
secure alternative is an **httpOnly cookie** (JS can't read it), but that
requires CSRF protection and more setup. For a portfolio MVP we choose
localStorage and document the caveat.

---

## Part 5 — Logout

There's intentionally **no `/logout` endpoint**. Because the JWT is stateless,
"logging out" = the client **deletes its stored token**. The server keeps no
session to clear.

> The catch: a stolen token stays valid until it expires. Real revocation needs
> a server-side **blocklist** (store revoked token ids) or short-lived access
> tokens + refresh tokens. We deferred refresh tokens, so we keep access tokens
> reasonably short-lived (60 min) and note this as a known limitation.

---

## File map

| File | Role |
|------|------|
| `app/core/config.py` | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_ALGORITHM` |
| `app/core/security.py` | bcrypt hash/verify + JWT encode/decode |
| `app/schemas/user.py` | `UserCreate` (input), `UserRead` (output, no hash) |
| `app/schemas/token.py` | `Token` (the login response shape) |
| `app/crud/user.py` | DB reads/writes for users |
| `app/api/deps.py` | `get_current_user` / `CurrentUser` gate |
| `app/api/auth.py` | the `/auth/signup`, `/auth/login`, `/auth/me` routes |

➡️ Next up: Boards (create/list) — the first endpoints that *use* `CurrentUser`.
