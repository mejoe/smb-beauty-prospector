import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table'
import {
  Building2, Instagram, ExternalLink, Upload, Search,
  ChevronUp, ChevronDown, ChevronsUpDown, X, Linkedin,
  RefreshCw, Download
} from 'lucide-react'
import { companiesApi, sessionsApi } from '../lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

interface Company {
  id: string
  name: string
  city?: string
  state?: string
  category?: string
  address?: string
  phone?: string
  website?: string
  instagram_handle?: string
  instagram_followers?: number
  linkedin_url?: string
  yelp_rating?: number
  yelp_review_count?: number
  status: string
  source?: string
  notes?: string
  created_at: string
  contact_count?: number
}

interface Session {
  id: string
  name: string
  search_config?: Record<string, unknown>
}

// ─── Detail Drawer ────────────────────────────────────────────────────────────

function CompanyDrawer({ company, onClose }: { company: Company; onClose: () => void }) {
  const { data } = useQuery({
    queryKey: ['company', company.id],
    queryFn: () => companiesApi.get(company.id).then(r => r.data),
  })
  const detail = data || company

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-[480px] bg-white h-full shadow-2xl flex flex-col overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{detail.name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-5">
          {/* Location */}
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Location</h3>
            <p className="text-sm text-gray-700">
              {[detail.address, detail.city, detail.state].filter(Boolean).join(', ') || '—'}
            </p>
          </div>
          {/* Industry */}
          {detail.category && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Industry</h3>
              <span className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">
                {detail.category.replace(/_/g, ' ')}
              </span>
            </div>
          )}
          {/* Contact info */}
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Contact</h3>
            <div className="space-y-1">
              {detail.phone && <p className="text-sm text-gray-700">📞 {detail.phone}</p>}
              {detail.website && (
                <a href={detail.website} target="_blank" rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline flex items-center gap-1">
                  <ExternalLink className="w-3 h-3" /> {detail.website}
                </a>
              )}
            </div>
          </div>
          {/* Social */}
          {(detail.instagram_handle || detail.linkedin_url) && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Social</h3>
              {detail.instagram_handle && (
                <a href={`https://instagram.com/${detail.instagram_handle}`} target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-pink-600 hover:text-pink-700 mb-1">
                  <Instagram className="w-4 h-4" />
                  @{detail.instagram_handle}
                  {detail.instagram_followers && (
                    <span className="text-xs text-gray-400">
                      ({detail.instagram_followers.toLocaleString()} followers)
                    </span>
                  )}
                </a>
              )}
              {detail.linkedin_url && (
                <a href={detail.linkedin_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800">
                  <Linkedin className="w-4 h-4" /> LinkedIn Profile
                </a>
              )}
            </div>
          )}
          {/* Yelp */}
          {detail.yelp_rating && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Yelp</h3>
              <p className="text-sm text-gray-700">
                ⭐ {detail.yelp_rating} ({detail.yelp_review_count} reviews)
              </p>
            </div>
          )}
          {/* Stats */}
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">CRM</h3>
            <div className="flex items-center gap-3">
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                detail.status === 'prospect' ? 'bg-gray-100 text-gray-600' :
                detail.status === 'contacted' ? 'bg-blue-100 text-blue-700' :
                detail.status === 'qualified' ? 'bg-green-100 text-green-700' :
                'bg-red-100 text-red-700'
              }`}>{detail.status}</span>
              {(detail as Company & { contact_count?: number }).contact_count !== undefined && (
                <span className="text-xs text-gray-500">
                  {(detail as Company & { contact_count?: number }).contact_count} contact(s)
                </span>
              )}
            </div>
          </div>
          {detail.notes && (
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Notes</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{detail.notes}</p>
            </div>
          )}
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Source</h3>
            <p className="text-sm text-gray-500">{detail.source || 'manual'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

const columnHelper = createColumnHelper<Company>()

export function Companies() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Filter state
  const [filterIndustry, setFilterIndustry] = useState('')
  const [filterCity, setFilterCity] = useState('')
  const [filterHasInstagram, setFilterHasInstagram] = useState<string>('')

  // Sorting
  const [sorting, setSorting] = useState<SortingState>([])

  // Selected company for drawer
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)

  // Toast messages
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const showToast = (type: 'success' | 'error', msg: string) => {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3500)
  }

  // Build query params
  const queryParams: Record<string, unknown> = { limit: 500 }
  if (filterIndustry) queryParams.category = filterIndustry
  if (filterCity) queryParams.city = filterCity
  if (filterHasInstagram === 'yes') queryParams.has_instagram = true
  if (filterHasInstagram === 'no') queryParams.has_instagram = false

  const { data, isLoading } = useQuery({
    queryKey: ['companies', queryParams],
    queryFn: () => companiesApi.list(queryParams).then(r => r.data),
  })
  const companies: Company[] = data || []

  // Sessions for "Discover More"
  const { data: sessionsData } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionsApi.list().then(r => r.data),
  })
  const sessions: Session[] = sessionsData || []
  const activeSession = sessions.find((s: Session) => s.search_config) || sessions[0]

  // Discover mutation
  const discoverMutation = useMutation({
    mutationFn: () => {
      if (!activeSession) throw new Error('No active session')
      return companiesApi.search(activeSession.id, activeSession.search_config || {})
    },
    onSuccess: () => {
      showToast('success', 'Discovery job queued! New companies will appear shortly.')
      queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
    onError: () => showToast('error', 'Failed to start discovery. Make sure you have an active session.'),
  })

  // Import CSV mutation
  const importMutation = useMutation({
    mutationFn: (file: File) => companiesApi.import(file),
    onSuccess: (data) => {
      const { imported, skipped } = data.data
      showToast('success', `Imported ${imported} companies (${skipped} skipped as duplicates)`)
      queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
    onError: () => showToast('error', 'Import failed. Check that your file is a valid CSV.'),
  })

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) importMutation.mutate(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [importMutation])

  const handleExport = useCallback(async () => {
    try {
      const resp = await companiesApi.export(queryParams)
      const url = window.URL.createObjectURL(new Blob([resp.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `companies_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      showToast('error', 'Export failed')
    }
  }, [queryParams])

  // Table columns
  const columns = [
    columnHelper.accessor('name', {
      header: 'Name',
      cell: info => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 text-sm">{info.getValue()}</span>
          {info.row.original.website && (
            <a href={info.row.original.website} target="_blank" rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              className="text-gray-400 hover:text-gray-600">
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      ),
    }),
    columnHelper.accessor('city', {
      header: 'City',
      cell: info => (
        <span className="text-sm text-gray-600">
          {info.getValue()}{info.row.original.state ? `, ${info.row.original.state}` : ''}
        </span>
      ),
    }),
    columnHelper.accessor('state', { header: 'State', cell: info => <span className="text-sm text-gray-500">{info.getValue() || '—'}</span> }),
    columnHelper.accessor('category', {
      header: 'Industry',
      cell: info => info.getValue() ? (
        <span className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">
          {info.getValue()!.replace(/_/g, ' ')}
        </span>
      ) : <span className="text-gray-300">—</span>,
    }),
    columnHelper.accessor('instagram_handle', {
      header: 'Instagram',
      cell: info => info.getValue() ? (
        <a href={`https://instagram.com/${info.getValue()}`} target="_blank" rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          className="flex items-center gap-1 text-pink-600 hover:text-pink-700 text-sm">
          <Instagram className="w-3 h-3" />@{info.getValue()}
        </a>
      ) : <span className="text-xs text-gray-300">—</span>,
    }),
    columnHelper.accessor('contact_count', {
      header: 'Contacts',
      cell: info => <span className="text-sm text-gray-600">{info.getValue() ?? 0}</span>,
    }),
    columnHelper.accessor('status', {
      header: 'Status',
      cell: info => (
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${
          info.getValue() === 'prospect' ? 'bg-gray-100 text-gray-600' :
          info.getValue() === 'contacted' ? 'bg-blue-100 text-blue-700' :
          info.getValue() === 'qualified' ? 'bg-green-100 text-green-700' :
          'bg-red-100 text-red-700'
        }`}>{info.getValue()}</span>
      ),
    }),
  ]

  const table = useReactTable({
    data: companies,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
          <p className="text-gray-500 mt-1">{companies.length} companies</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importMutation.isPending}
            className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
          >
            <Upload className="w-4 h-4" />
            {importMutation.isPending ? 'Importing…' : 'Import CSV'}
          </button>
          <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleFileSelect} />
          <button
            onClick={() => discoverMutation.mutate()}
            disabled={discoverMutation.isPending || !activeSession}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${discoverMutation.isPending ? 'animate-spin' : ''}`} />
            {discoverMutation.isPending ? 'Discovering…' : 'Discover More'}
          </button>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm font-medium ${
          toast.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by city…"
            value={filterCity}
            onChange={e => setFilterCity(e.target.value)}
            className="pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300 w-44"
          />
        </div>
        <select
          value={filterIndustry}
          onChange={e => setFilterIndustry(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All Industries</option>
          <option value="medspa">MedSpa</option>
          <option value="plastic_surgery">Plastic Surgery</option>
          <option value="dermatology">Dermatology</option>
          <option value="functional_med">Functional Medicine</option>
          <option value="weightloss">Weight Loss</option>
        </select>
        <select
          value={filterHasInstagram}
          onChange={e => setFilterHasInstagram(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">Instagram: All</option>
          <option value="yes">Has Instagram</option>
          <option value="no">No Instagram</option>
        </select>
        {(filterCity || filterIndustry || filterHasInstagram) && (
          <button
            onClick={() => { setFilterCity(''); setFilterIndustry(''); setFilterHasInstagram('') }}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
          >
            <X className="w-3 h-3" /> Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-gray-500 py-8 text-center">Loading…</div>
      ) : companies.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Building2 className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No companies yet.</p>
          <p className="text-gray-400 text-sm mt-1">Import a CSV or click "Discover More" to find companies.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              {table.getHeaderGroups().map(hg => (
                <tr key={hg.id} className="border-b border-gray-200 bg-gray-50">
                  {hg.headers.map(header => (
                    <th
                      key={header.id}
                      className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3 cursor-pointer select-none whitespace-nowrap"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getCanSort() && (
                          header.column.getIsSorted() === 'asc' ? <ChevronUp className="w-3 h-3" /> :
                          header.column.getIsSorted() === 'desc' ? <ChevronDown className="w-3 h-3" /> :
                          <ChevronsUpDown className="w-3 h-3 text-gray-300" />
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-gray-100">
              {table.getRowModel().rows.map(row => (
                <tr
                  key={row.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedCompany(row.original)}
                >
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-4 py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Company detail drawer */}
      {selectedCompany && (
        <CompanyDrawer
          company={selectedCompany}
          onClose={() => setSelectedCompany(null)}
        />
      )}
    </div>
  )
}
