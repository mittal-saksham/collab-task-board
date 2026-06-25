// Shared TypeScript types mirroring the backend's response shapes.
// Keeping them in one place means the whole UI agrees on the data model.

export interface User {
  id: number;
  email: string;
  created_at: string;
}

// Minimal user shape returned where a user is *referenced* (e.g. a card's
// assignee). Mirrors the backend's UserBrief schema (id + email only).
export interface UserBrief {
  id: number;
  email: string;
}

// A colored, board-scoped tag that can be attached to cards. `color` is a plain
// name (e.g. "indigo"); the UI maps it to Tailwind classes via LABEL_STYLES.
export interface Label {
  id: number;
  name: string;
  color: string;
}

export interface Board {
  id: number;
  title: string;
  owner_id: number;
  created_at: string;
}

// Lists and Cards (used from the board view onward).
export interface Card {
  id: number;
  list_id: number;
  title: string;
  description: string | null;
  position: number;
  // --- Jira-style fields (G1). All present on every card: the backend backfills
  // priority='medium', and assignee/due_date are null + labels=[] by default. ---
  priority: string;          // one of: highest | high | medium | low | lowest
  due_date: string | null;   // ISO date "YYYY-MM-DD", or null
  issue_type: string;        // one of: task | bug | story (G3)
  story_points: number | null; // optional effort estimate (G3)
  assignee: UserBrief | null;
  labels: Label[];
  created_at: string;
  updated_at: string;
}

export interface List {
  id: number;
  board_id: number;
  title: string;
  position: number;
  wip_limit: number | null; // soft cap on card count; null = no limit (G3, display-only)
  created_at: string;
  cards: Card[];
}

// GET /boards/{id} returns the board with its nested lists + cards.
export interface BoardDetail extends Board {
  lists: List[];
}

export interface Member {
  user_id: number;
  email: string;
  role: string;
}

// A message posted on a card (the card's discussion thread).
export interface Comment {
  id: number;
  card_id: number;
  body: string;
  author: UserBrief;
  created_at: string;
}

// One entry in a board's activity feed. `actor` is null if that user was later
// removed; `card_id` is null for events not tied to a card (e.g. a member added).
export interface Activity {
  id: number;
  board_id: number;
  actor: UserBrief | null;
  card_id: number | null;
  verb: string;
  summary: string;
  created_at: string;
}
