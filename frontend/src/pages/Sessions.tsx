import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { sessionsApi } from '../lib/api'
import { Plus, ChevronRight, Trash2, MessageSquare } from 'lucide-react'

export function Sessions() {
  const qc = useQueryClient()
  const [newName, setNewName] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionsApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: () => sessionsApi.create(newName),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      setNewName('')
      setShowCreate(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => sessionsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  })

  const sessions = data?.data || []

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Research Sessions</h1>
          <p className="text-gray-500 mt-1">Organize your prospecting by market or campaign</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" /> New Session
        </button>
      </div>

      {showCreate && (
        <div className="mb-6 p-4 bg-white rounded-xl border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Create New Session</h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Austin MedSpas Q1 2026"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              onKeyDown={(e) => e.key === 'Enter' && newName && createMutation.mutate()}
            />
            <button
              onClick={() => createMutation.mutate()}
              disabled={!newName || createMutation.isPending}
              className="px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
            >
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <MessageSquare className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No sessions yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((s: { id: string; name: string; status: string; created_at: string; description?: string }) => (
            <div key={s.id} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
              <div>
                <Link
                  to={`/sessions/${s.id}/chat`}
                  className="text-base font-semibold text-gray-900 hover:text-brand-600"
                >
                  {s.name}
                </Link>
                {s.description && <p className="text-sm text-gray-500 mt-0.5">{s.description}</p>}
                <p className="text-xs text-gray-400 mt-1">
                  Created {new Date(s.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                  s.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {s.status}
                </span>
                <Link to={`/sessions/${s.id}/chat`} className="text-brand-600 hover:text-brand-700">
                  <ChevronRight className="w-5 h-5" />
                </Link>
                <button
                  onClick={() => {
                    if (confirm('Delete this session?')) deleteMutation.mutate(s.id)
                  }}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
