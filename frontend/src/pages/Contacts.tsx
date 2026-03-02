import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contactsApi } from '../lib/api'
import { Users, Instagram, ExternalLink, Zap } from 'lucide-react'

export function Contacts() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => contactsApi.list({ limit: 200 }),
  })

  const enrichMutation = useMutation({
    mutationFn: (id: string) => contactsApi.enrich(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] }),
  })

  const contacts = data?.data || []

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Contacts</h1>
        <p className="text-gray-500 mt-1">{contacts.length} contacts in your database</p>
      </div>

      {isLoading ? (
        <div className="text-gray-500">Loading...</div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Users className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No contacts yet. Import from CSV or run company discovery.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Name</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Role</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Instagram</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">LinkedIn</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Status</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {contacts.map((c: {
                id: string; name: string; role?: string; credentials?: string;
                instagram_handle?: string; linkedin_url?: string; status: string;
                enrichment_status: string;
              }) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div>
                      <span className="font-medium text-gray-900 text-sm">{c.name}</span>
                      {c.credentials && <span className="ml-1 text-xs text-gray-500">{c.credentials}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.role || '—'}</td>
                  <td className="px-4 py-3">
                    {c.instagram_handle ? (
                      <a
                        href={`https://instagram.com/${c.instagram_handle}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-pink-600 hover:text-pink-700 text-sm"
                      >
                        <Instagram className="w-3 h-3" />
                        @{c.instagram_handle}
                      </a>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {c.linkedin_url ? (
                      <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-700">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      c.status === 'prospect' ? 'bg-gray-100 text-gray-600' :
                      c.status === 'contacted' ? 'bg-blue-100 text-blue-700' :
                      c.status === 'qualified' ? 'bg-green-100 text-green-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => enrichMutation.mutate(c.id)}
                      disabled={enrichMutation.isPending}
                      title="Enrich Instagram & LinkedIn"
                      className="text-gray-400 hover:text-brand-500 transition-colors"
                    >
                      <Zap className="w-4 h-4" />
                    </button>
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
