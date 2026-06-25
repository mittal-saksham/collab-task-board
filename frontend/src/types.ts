// Shared TypeScript types mirroring the backend's response shapes.
// Keeping them in one place means the whole UI agrees on the data model.

export interface User {
  id: number;
  email: string;
  created_at: string;
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
  created_at: string;
  updated_at: string;
}

export interface List {
  id: number;
  board_id: number;
  title: string;
  position: number;
  created_at: string;
  cards: Card[];
}

// GET /boards/{id} returns the board with its nested lists + cards.
export interface BoardDetail extends Board {
  lists: List[];
}
