"""Single-use, short-lived tickets for authenticating WebSocket connections.

The problem: browsers can't set an Authorization header on a WebSocket
handshake, so the credential has to ride in the URL — and URLs (including the
query string) land in server/proxy access logs. Putting the real JWT there
means a leaked log line grants full API access for the token's remaining
lifetime.

The fix is the standard "ticket" pattern:
  1. The client (already authenticated) POSTs /auth/ws-ticket over HTTPS.
  2. We mint a random single-use ticket bound to that user, valid ~60s.
  3. The client connects `WS /ws/boards/{id}?ticket=...`; the server redeems
     (and thereby BURNS) the ticket before accepting.

A logged ticket is worthless: it's already consumed, expires within a minute
anyway, and never grants REST access.

Storage is an in-memory dict — per-process, same trade-off as the WS manager
itself (a multi-instance deploy would move both to Redis). Expired tickets are
purged opportunistically on each issue, so the dict can't grow unbounded.
"""

import secrets
import threading
import time

TICKET_TTL_SECONDS = 60.0

_tickets: dict[str, tuple[int, float]] = {}  # ticket -> (user_id, expires_at)
_lock = threading.Lock()


def issue(user_id: int) -> str:
    """Mint a ticket for a user. token_urlsafe(32) = 256 bits — unguessable."""
    ticket = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _lock:
        # Opportunistic purge (cheap: tickets are few and short-lived).
        expired = [t for t, (_, exp) in _tickets.items() if exp < now]
        for t in expired:
            del _tickets[t]
        _tickets[ticket] = (user_id, now + TICKET_TTL_SECONDS)
    return ticket


def redeem(ticket: str) -> int | None:
    """Consume a ticket and return its user_id; None if unknown/expired/reused.

    `pop` makes redemption atomic and single-use: a second redeem of the same
    ticket finds nothing — even if the first redeem was by an eavesdropper,
    the legitimate client's failure is at least visible (connect rejected).
    """
    with _lock:
        entry = _tickets.pop(ticket, None)
    if entry is None:
        return None
    user_id, expires_at = entry
    if time.monotonic() > expires_at:
        return None
    return user_id
