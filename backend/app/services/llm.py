"""Optional, isolated "summarize this board" feature, powered by Claude.

Kept in its own module so the whole AI piece can be enabled or disabled with a
single env var (ANTHROPIC_API_KEY) without touching any core logic. If the key
is absent, the route returns 503 and nothing else in the app is affected.
"""

import anthropic

from app.core.config import settings
from app.models.board import Board


class SummarizerNotConfigured(Exception):
    """Raised when ANTHROPIC_API_KEY isn't set."""


class SummarizerError(Exception):
    """Raised when the LLM request itself fails."""


def _board_to_text(board: Board) -> str:
    """Flatten a board's columns + cards into plain text for the prompt."""
    lines = [f"Board: {board.title}"]
    for column in board.lists:  # ordered by position via the ORM relationship
        lines.append(f"\nColumn: {column.title}")
        if not column.cards:
            lines.append("  (no cards)")
        for card in column.cards:
            description = f" — {card.description}" if card.description else ""
            lines.append(f"  - {card.title}{description}")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are a concise project assistant. Given a task board's columns and "
    "cards, write a short summary (3-5 sentences) covering what the board is "
    "about, what's in progress, and any notable gaps or imbalances. Use plain "
    "prose — no markdown headings or bullet lists."
)


def summarize_board(board: Board) -> str:
    """Return a short natural-language summary of a board via Claude.

    Raises SummarizerNotConfigured if no API key; SummarizerError on API failure.
    """
    if not settings.anthropic_api_key:
        raise SummarizerNotConfigured()

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model=settings.summarizer_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _board_to_text(board)}],
        )
    except anthropic.APIError as exc:  # network/auth/rate-limit/etc.
        raise SummarizerError(str(exc)) from exc

    # Concatenate the text blocks of the response (skip any non-text blocks).
    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
