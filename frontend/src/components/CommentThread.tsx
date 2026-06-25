import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useBoardMutations, useComments } from '../hooks'
import { initials, timeAgo } from '../lib/time'

// The discussion thread shown inside a card's detail modal: a list of comments
// (oldest first) plus a box to add one. You can delete only your OWN comments.
export function CommentThread({
  cardId,
  boardId,
}: {
  cardId: number
  boardId: number
}) {
  const { user } = useAuth()
  const { data: comments = [], isLoading } = useComments(cardId)
  const m = useBoardMutations(boardId)
  const [body, setBody] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    const text = body.trim()
    if (!text) return
    m.createComment.mutate({ cardId, body: text })
    setBody('') // optimistic clear; the refetch brings the saved comment in
  }

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Comments {comments.length > 0 && `(${comments.length})`}
      </p>

      <ul className="space-y-3">
        {isLoading && <li className="text-sm text-slate-400">Loading…</li>}
        {!isLoading && comments.length === 0 && (
          <li className="text-sm text-slate-400">No comments yet.</li>
        )}
        {comments.map((c) => (
          <li key={c.id} className="flex gap-2">
            {/* author avatar */}
            <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-semibold text-white">
              {initials(c.author.email)}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <span className="truncate text-xs font-medium text-slate-700">
                  {c.author.email}
                </span>
                <span className="text-[11px] text-slate-400">
                  {timeAgo(c.created_at)}
                </span>
                {/* delete only your own comments */}
                {user?.id === c.author.id && (
                  <button
                    onClick={() =>
                      m.deleteComment.mutate({ cardId, commentId: c.id })
                    }
                    title="Delete comment"
                    className="ml-auto text-slate-300 hover:text-red-500"
                  >
                    ×
                  </button>
                )}
              </div>
              <p className="whitespace-pre-wrap break-words text-sm text-slate-700">
                {c.body}
              </p>
            </div>
          </li>
        ))}
      </ul>

      <form onSubmit={submit} className="mt-3 flex gap-2">
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Write a comment…"
          className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm outline-none focus:border-indigo-400"
        />
        <button
          type="submit"
          disabled={!body.trim() || m.createComment.isPending}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
