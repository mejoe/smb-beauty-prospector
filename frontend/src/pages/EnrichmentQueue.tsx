import { useQuery } from '@tanstack/react-query'
import { jobsApi } from '../lib/api'
import { Sparkles, CheckCircle, XCircle, Clock, Loader } from 'lucide-react'

export function EnrichmentQueue() {
  const { data, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list(),
    refetchInterval: 5000,
  })

  const jobs = data?.data || []

  const statusIcon = (status: string) => {
    switch (status) {
      case 'complete': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-500" />
      case 'running': return <Loader className="w-4 h-4 text-blue-500 animate-spin" />
      default: return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Enrichment Queue</h1>
        <p className="text-gray-500 mt-1">Track Instagram and LinkedIn enrichment jobs</p>
      </div>

      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Sparkles className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No enrichment jobs yet. Trigger enrichment from a contact.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Status</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Type</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Entity</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Created</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((j: {
                id: string; status: string; job_type: string;
                entity_type: string; entity_id: string; created_at: string; error?: string;
              }) => (
                <tr key={j.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{statusIcon(j.status)}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{j.job_type.replace('_', ' ')}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 font-mono">{j.entity_type}:{j.entity_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{new Date(j.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-xs text-red-600">{j.error || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
