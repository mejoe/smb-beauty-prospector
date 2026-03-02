import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { instagramApi, jobsApi } from '../lib/api'
import {
  Sparkles, CheckCircle, XCircle, Clock, Loader,
  Instagram, Zap, RefreshCw,
} from 'lucide-react'

interface Job {
  id: string
  entity_id: string
  contact_name?: string
  contact_ig?: string
  ig_confidence_score?: number
  ig_match_method?: string
  job_type: string
  status: string
  error?: string
  result?: unknown
  created_at: string
  completed_at?: string
}

const statusIcon = (s: string) => {
  switch (s) {
    case 'complete': return <CheckCircle className="w-4 h-4 text-green-500" />
    case 'failed': return <XCircle className="w-4 h-4 text-red-500" />
    case 'running': return <Loader className="w-4 h-4 text-blue-500 animate-spin" />
    default: return <Clock className="w-4 h-4 text-gray-400" />
  }
}

const methodBadge = (method?: string) => {
  if (!method) return null
  const labels: Record<string, { label: string; color: string }> = {
    followers_scrape: { label: 'Method A (followers)', color: 'bg-purple-100 text-purple-700' },
    name_search: { label: 'Method B (name search)', color: 'bg-blue-100 text-blue-700' },
    hashtag: { label: 'Method C (hashtag)', color: 'bg-orange-100 text-orange-700' },
    manual: { label: 'Manual', color: 'bg-gray-100 text-gray-700' },
  }
  const info = labels[method] || { label: method, color: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${info.color}`}>
      {info.label}
    </span>
  )
}

export function EnrichmentQueue() {
  const qc = useQueryClient()

  const { data: queueData, isLoading } = useQuery({
    queryKey: ['ig-queue'],
    queryFn: () => instagramApi.getQueue(),
    refetchInterval: 5000,
  })

  const { data: sessionData } = useQuery({
    queryKey: ['ig-session'],
    queryFn: () => instagramApi.sessionStatus(),
  })

  const enrichAllMutation = useMutation({
    mutationFn: () => instagramApi.enrichAllPending(),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['ig-queue'] })
      alert(`Queued ${res.data.queued} contacts for enrichment`)
    },
  })

  const jobs: Job[] = queueData?.data || []
  const session = sessionData?.data
  const runningCount = jobs.filter((j) => j.status === 'running').length
  const completeCount = jobs.filter((j) => j.status === 'complete').length
  const pendingCount = jobs.filter((j) => j.status === 'queued').length

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Enrichment Queue</h1>
          <p className="text-gray-500 mt-0.5">
            Instagram enrichment jobs — {jobs.length} total
            {runningCount > 0 && (
              <span className="ml-2 text-blue-600 font-medium">{runningCount} running</span>
            )}
          </p>
        </div>
        <button
          onClick={() => enrichAllMutation.mutate()}
          disabled={enrichAllMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
        >
          <Zap className="w-4 h-4" />
          {enrichAllMutation.isPending ? 'Queuing...' : 'Enrich All Pending'}
        </button>
      </div>

      {/* Session Status Banner */}
      <div className={`flex items-center gap-3 p-4 rounded-xl border mb-6 ${
        session?.connected
          ? 'bg-green-50 border-green-200'
          : 'bg-amber-50 border-amber-200'
      }`}>
        <Instagram className={`w-5 h-5 ${session?.connected ? 'text-green-600' : 'text-amber-500'}`} />
        {session?.connected ? (
          <div>
            <p className="text-sm font-medium text-green-800">
              Instagram connected — @{session.username}
            </p>
            <p className="text-xs text-green-600">
              Live enrichment active · Session expires {session.expires_at ? new Date(session.expires_at).toLocaleDateString() : 'unknown'}
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium text-amber-800">No Instagram session connected</p>
            <p className="text-xs text-amber-600">
              Running in stub mode — connect your Instagram account in Settings for real enrichment
            </p>
          </div>
        )}
      </div>

      {/* Stats row */}
      {jobs.length > 0 && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total', value: jobs.length, color: 'text-gray-900' },
            { label: 'Running', value: runningCount, color: 'text-blue-600' },
            { label: 'Complete', value: completeCount, color: 'text-green-600' },
            { label: 'Queued', value: pendingCount, color: 'text-gray-500' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Queue table */}
      {isLoading ? (
        <div className="text-gray-500 py-8">Loading...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Sparkles className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No enrichment jobs yet.</p>
          <p className="text-sm text-gray-400 mt-1">
            Click "Enrich All Pending" or trigger enrichment from the Contacts page.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {['Status', 'Contact', 'Instagram Found', 'Confidence', 'Method', 'Time'].map((h) => (
                  <th
                    key={h}
                    className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((j) => (
                <tr key={j.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{statusIcon(j.status)}</td>
                  <td className="px-4 py-3">
                    <span className="text-sm font-medium text-gray-900">
                      {j.contact_name || <span className="text-gray-400 font-mono text-xs">{j.entity_id.slice(0, 8)}…</span>}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {j.contact_ig ? (
                      <a
                        href={`https://instagram.com/${j.contact_ig}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-pink-600 hover:text-pink-700 text-sm"
                      >
                        <Instagram className="w-3 h-3" />
                        @{j.contact_ig}
                      </a>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {j.ig_confidence_score != null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-1.5">
                          <div
                            className="bg-green-500 h-1.5 rounded-full"
                            style={{ width: `${Math.round(j.ig_confidence_score * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">
                          {Math.round(j.ig_confidence_score * 100)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{methodBadge(j.ig_match_method)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {new Date(j.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
