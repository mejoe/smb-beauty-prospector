import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { outreachApi } from '../lib/api'
import { Send, Plus, PauseCircle, PlayCircle } from 'lucide-react'

export function Outreach() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newTemplate, setNewTemplate] = useState(
    "Hi {{first_name}}, I noticed you work at {{company}}! I'd love to connect about..."
  )
  const [confirmCampaignId, setConfirmCampaignId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => outreachApi.listCampaigns(),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      outreachApi.createCampaign({ name: newName, message_template: newTemplate }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] })
      setShowCreate(false)
      setNewName('')
    },
  })

  const startMutation = useMutation({
    mutationFn: (id: string) => outreachApi.startCampaign(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] })
      setConfirmCampaignId(null)
    },
  })

  const pauseMutation = useMutation({
    mutationFn: (id: string) => outreachApi.pauseCampaign(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  })

  const campaigns = data?.data || []

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Outreach Campaigns</h1>
          <p className="text-gray-500 mt-1">Send personalized Instagram DMs to prospects</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium"
        >
          <Plus className="w-4 h-4" /> New Campaign
        </button>
      </div>

      {/* Confirmation modal */}
      {confirmCampaignId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold text-gray-900 mb-2">⚠️ Start Campaign?</h2>
            <p className="text-gray-600 text-sm mb-4">
              This will queue Instagram DMs for sending. In <strong>development mode</strong>,
              no actual sends will execute. In production, real DMs will be sent to contacts.
              Make sure you have reviewed all messages before proceeding.
            </p>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
              <p className="text-yellow-800 text-xs font-medium">
                ⚠️ Instagram DMs are subject to platform limits (max 30/day).
                Misuse may result in account restrictions.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => startMutation.mutate(confirmCampaignId)}
                className="flex-1 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium"
              >
                {startMutation.isPending ? 'Starting...' : 'Yes, Start Campaign'}
              </button>
              <button
                onClick={() => setConfirmCampaignId(null)}
                className="flex-1 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="mb-6 p-6 bg-white rounded-xl border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-4">New Campaign</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g. Austin MedSpa Owners Q1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Message Template
                <span className="ml-2 text-xs text-gray-400 font-normal">
                  Variables: {'{{first_name}} {{name}} {{company}} {{role}}'}
                </span>
              </label>
              <textarea
                value={newTemplate}
                onChange={(e) => setNewTemplate(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => createMutation.mutate()}
                disabled={!newName || !newTemplate || createMutation.isPending}
                className="px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
              >
                Create
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-gray-600 text-sm">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Send className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No campaigns yet. Create one to start reaching out.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c: {
            id: string; name: string; status: string; platform: string;
            daily_send_limit: number; created_at: string; message_template?: string;
          }) => (
            <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{c.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {c.platform.replace('_', ' ')} · Max {c.daily_send_limit}/day
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    c.status === 'draft' ? 'bg-gray-100 text-gray-600' :
                    c.status === 'active' ? 'bg-green-100 text-green-700' :
                    c.status === 'paused' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>{c.status}</span>
                  {(c.status === 'draft' || c.status === 'paused') && (
                    <button
                      onClick={() => setConfirmCampaignId(c.id)}
                      className="text-green-600 hover:text-green-700"
                      title="Start campaign"
                    >
                      <PlayCircle className="w-5 h-5" />
                    </button>
                  )}
                  {c.status === 'active' && (
                    <button
                      onClick={() => pauseMutation.mutate(c.id)}
                      className="text-yellow-600 hover:text-yellow-700"
                      title="Pause campaign"
                    >
                      <PauseCircle className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
              {c.message_template && (
                <p className="mt-3 text-sm text-gray-600 bg-gray-50 rounded-lg p-3 italic truncate">
                  "{c.message_template}"
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
