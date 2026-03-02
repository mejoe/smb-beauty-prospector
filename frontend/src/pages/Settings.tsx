import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { instagramApi } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { Instagram, CheckCircle, XCircle } from 'lucide-react'

export function Settings() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [igUsername, setIgUsername] = useState('')
  const [igCookies, setIgCookies] = useState('')

  const { data: igStatus } = useQuery({
    queryKey: ['ig-session'],
    queryFn: () => instagramApi.sessionStatus(),
  })

  const saveMutation = useMutation({
    mutationFn: () => instagramApi.saveSession(igUsername, igCookies),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ig-session'] })
      setIgCookies('')
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: () => instagramApi.deleteSession(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ig-session'] }),
  })

  const status = igStatus?.data

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure your account and integrations</p>
      </div>

      {/* Instagram Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <Instagram className="w-5 h-5 text-pink-500" />
          <h2 className="text-lg font-semibold text-gray-900">Instagram Account</h2>
        </div>

        {status?.connected ? (
          <div>
            <div className="flex items-center gap-2 text-green-600 mb-3">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Connected as @{status.username}</span>
            </div>
            <p className="text-xs text-gray-500 mb-4">
              Session valid since: {status.valid_at ? new Date(status.valid_at).toLocaleDateString() : 'Unknown'}
            </p>
            <button
              onClick={() => disconnectMutation.mutate()}
              className="px-4 py-2 border border-red-300 text-red-600 hover:bg-red-50 rounded-lg text-sm font-medium"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2 text-red-500 mb-4">
              <XCircle className="w-4 h-4" />
              <span className="text-sm">Not connected</span>
            </div>
            <p className="text-xs text-gray-500 mb-4">
              To connect Instagram, log in via your browser, export the session cookies,
              and paste them below. This enables Instagram enrichment and outreach.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Instagram Username</label>
                <input
                  type="text"
                  value={igUsername}
                  onChange={(e) => setIgUsername(e.target.value)}
                  placeholder="@your_username"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Session Cookies (JSON)
                </label>
                <textarea
                  value={igCookies}
                  onChange={(e) => setIgCookies(e.target.value)}
                  rows={4}
                  placeholder='{"sessionid": "...", "ds_user_id": "..."}'
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <button
                onClick={() => saveMutation.mutate()}
                disabled={!igUsername || !igCookies || saveMutation.isPending}
                className="px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
              >
                {saveMutation.isPending ? 'Saving...' : 'Connect Account'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Account Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Account</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Email</span>
            <span className="text-gray-900">{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Plan</span>
            <span className="text-gray-900 capitalize">{user?.subscription_tier}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
