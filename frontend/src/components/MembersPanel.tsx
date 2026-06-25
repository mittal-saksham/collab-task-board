import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useAddMember, useMembers, useRemoveMember } from '../hooks'

// A small dropdown panel listing a board's members. The owner can invite (by
// email) and remove members; everyone else just sees the list.
export function MembersPanel({
  boardId,
  ownerId,
  onClose,
}: {
  boardId: number
  ownerId: number
  onClose: () => void
}) {
  const { user } = useAuth()
  const isOwner = user?.id === ownerId
  const { data: members } = useMembers(boardId)
  const addMember = useAddMember(boardId)
  const removeMember = useRemoveMember(boardId)
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function invite(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await addMember.mutateAsync(email.trim())
      setEmail('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invite')
    }
  }

  return (
    <div className="absolute right-0 top-10 z-10 w-72 rounded-lg border border-slate-200 bg-white p-4 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">Members</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          ×
        </button>
      </div>

      <ul className="mb-3 space-y-1">
        {members?.map((m) => (
          <li key={m.user_id} className="flex items-center justify-between text-sm">
            <span className="truncate text-slate-700">{m.email}</span>
            <span className="ml-2 flex items-center gap-2">
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                {m.role}
              </span>
              {isOwner && m.role !== 'owner' && (
                <button
                  onClick={() => removeMember.mutate(m.user_id)}
                  title="Remove member"
                  className="text-slate-300 hover:text-red-500"
                >
                  ×
                </button>
              )}
            </span>
          </li>
        ))}
      </ul>

      {isOwner ? (
        <form onSubmit={invite} className="space-y-2">
          {error && <p className="text-xs text-red-600">{error}</p>}
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Invite by email"
            className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={addMember.isPending}
            className="w-full rounded-md bg-indigo-600 py-1 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Invite
          </button>
        </form>
      ) : (
        <p className="text-xs text-slate-400">Only the owner can invite members.</p>
      )}
    </div>
  )
}
