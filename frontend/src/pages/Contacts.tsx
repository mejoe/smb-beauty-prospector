import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
  type ColumnFiltersState,
} from '@tanstack/react-table'
import { contactsApi } from '../lib/api'
import {
  Users, Instagram, ExternalLink, Zap, Upload, Download,
  X, ChevronLeft, ChevronRight, Search, Mail, Linkedin,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Contact {
  id: string
  name: string
  role?: string
  credentials?: string
  company_id?: string
  email?: string
  phone?: string
  linkedin_url?: string
  instagram_handle?: string
  instagram_followers?: number
  instagram_bio?: string
  ig_confidence_score?: number
  enrichment_status: string
  status: string
  crm_notes?: string
  tags?: string[]
  source?: string
  created_at: string
}

// ─── Contact Detail Drawer ────────────────────────────────────────────────────

function ContactDrawer({
  contact,
  onClose,
}: {
  contact: Contact
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="flex-1 bg-black/30" onClick={onClose} />

      {/* Panel */}
      <div className="w-full max-w-md bg-white shadow-2xl flex flex-col overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{contact.name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-5">
          {/* Role & Credentials */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Role</p>
            <p className="text-gray-800">
              {contact.role || '—'}
              {contact.credentials && (
                <span className="ml-2 text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                  {contact.credentials}
                </span>
              )}
            </p>
          </div>

          {/* Contact Info */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Contact</p>
            <div className="space-y-1.5">
              {contact.email ? (
                <a
                  href={`mailto:${contact.email}`}
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                >
                  <Mail className="w-4 h-4" />
                  {contact.email}
                </a>
              ) : (
                <p className="text-sm text-gray-400">No email</p>
              )}
              {contact.linkedin_url && (
                <a
                  href={contact.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                >
                  <Linkedin className="w-4 h-4" />
                  LinkedIn Profile
                </a>
              )}
              {contact.instagram_handle && (
                <a
                  href={`https://instagram.com/${contact.instagram_handle}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-pink-600 hover:text-pink-700"
                >
                  <Instagram className="w-4 h-4" />
                  @{contact.instagram_handle}
                  {contact.instagram_followers && (
                    <span className="text-xs text-gray-400">
                      ({contact.instagram_followers.toLocaleString()} followers)
                    </span>
                  )}
                </a>
              )}
            </div>
          </div>

          {/* Instagram Bio */}
          {contact.instagram_bio && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">IG Bio</p>
              <p className="text-sm text-gray-600">{contact.instagram_bio}</p>
            </div>
          )}

          {/* Enrichment */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Enrichment</p>
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${
              contact.enrichment_status === 'complete' ? 'bg-green-100 text-green-700' :
              contact.enrichment_status === 'pending' ? 'bg-gray-100 text-gray-600' :
              contact.enrichment_status === 'running' ? 'bg-blue-100 text-blue-700' :
              'bg-red-100 text-red-700'
            }`}>
              {contact.enrichment_status}
            </span>
            {contact.ig_confidence_score != null && (
              <span className="ml-2 text-xs text-gray-500">
                IG confidence: {Math.round(contact.ig_confidence_score * 100)}%
              </span>
            )}
          </div>

          {/* CRM Status */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Status</p>
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${
              contact.status === 'prospect' ? 'bg-gray-100 text-gray-600' :
              contact.status === 'contacted' ? 'bg-blue-100 text-blue-700' :
              contact.status === 'qualified' ? 'bg-green-100 text-green-700' :
              'bg-red-100 text-red-700'
            }`}>
              {contact.status}
            </span>
          </div>

          {/* Notes */}
          {contact.crm_notes && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Notes</p>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{contact.crm_notes}</p>
            </div>
          )}

          {/* Source */}
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Source</p>
            <p className="text-sm text-gray-500">{contact.source || '—'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Main Contacts Page ───────────────────────────────────────────────────────

const columnHelper = createColumnHelper<Contact>()

export function Contacts() {
  const qc = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Filters
  const [titleFilter, setTitleFilter] = useState('')
  const [hasEmail, setHasEmail] = useState<boolean | undefined>(undefined)
  const [hasInstagram, setHasInstagram] = useState<boolean | undefined>(undefined)
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])

  // Selected contact for drawer
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null)

  // Build query params
  const queryParams: Record<string, unknown> = { limit: 500 }
  if (titleFilter) queryParams.title = titleFilter
  if (hasEmail !== undefined) queryParams.has_email = hasEmail
  if (hasInstagram !== undefined) queryParams.has_instagram = hasInstagram

  const { data, isLoading } = useQuery({
    queryKey: ['contacts', queryParams],
    queryFn: () => contactsApi.list(queryParams),
  })

  const enrichMutation = useMutation({
    mutationFn: (id: string) => contactsApi.enrich(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] }),
  })

  const importMutation = useMutation({
    mutationFn: (file: File) => contactsApi.importCsv(file),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['contacts'] })
      alert(`Imported ${res.data.imported} contacts (${res.data.skipped} skipped)`)
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Import failed'
      alert(msg)
    },
  })

  const contacts: Contact[] = data?.data || []

  // ── Columns ────────────────────────────────────────────────────────────────

  const columns = [
    columnHelper.accessor('name', {
      header: 'Name',
      cell: (info) => (
        <div>
          <span className="font-medium text-gray-900 text-sm">{info.getValue()}</span>
          {info.row.original.credentials && (
            <span className="ml-1.5 text-xs text-gray-400">{info.row.original.credentials}</span>
          )}
        </div>
      ),
    }),
    columnHelper.accessor('role', {
      header: 'Title',
      cell: (info) => (
        <span className="text-sm text-gray-600">{info.getValue() || '—'}</span>
      ),
    }),
    columnHelper.accessor('email', {
      header: 'Email',
      cell: (info) =>
        info.getValue() ? (
          <a href={`mailto:${info.getValue()}`} className="text-sm text-blue-600 hover:underline">
            {info.getValue()}
          </a>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        ),
    }),
    columnHelper.accessor('linkedin_url', {
      header: 'LinkedIn',
      cell: (info) =>
        info.getValue() ? (
          <a
            href={info.getValue()!}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        ),
    }),
    columnHelper.accessor('instagram_handle', {
      header: 'Instagram',
      cell: (info) =>
        info.getValue() ? (
          <a
            href={`https://instagram.com/${info.getValue()}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-pink-600 hover:text-pink-700 text-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <Instagram className="w-3 h-3" />
            @{info.getValue()}
          </a>
        ) : (
          <span className="text-xs text-gray-300">—</span>
        ),
    }),
    columnHelper.accessor('enrichment_status', {
      header: 'Enrichment',
      cell: (info) => (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          info.getValue() === 'complete' ? 'bg-green-100 text-green-700' :
          info.getValue() === 'pending' ? 'bg-gray-100 text-gray-500' :
          info.getValue() === 'running' ? 'bg-blue-100 text-blue-700' :
          'bg-red-100 text-red-600'
        }`}>
          {info.getValue()}
        </span>
      ),
    }),
    columnHelper.display({
      id: 'actions',
      header: '',
      cell: (info) => (
        <button
          onClick={(e) => {
            e.stopPropagation()
            enrichMutation.mutate(info.row.original.id)
          }}
          disabled={enrichMutation.isPending}
          title="Enrich Instagram & LinkedIn"
          className="text-gray-300 hover:text-brand-500 transition-colors"
        >
          <Zap className="w-4 h-4" />
        </button>
      ),
    }),
  ]

  // ── Table ──────────────────────────────────────────────────────────────────

  const table = useReactTable({
    data: contacts,
    columns,
    state: { columnFilters },
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 50 } },
  })

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleImport = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      importMutation.mutate(file)
      e.target.value = ''
    }
  }, [importMutation])

  const handleExport = useCallback(async () => {
    const params: Record<string, unknown> = {}
    if (hasEmail !== undefined) params.has_email = hasEmail
    if (hasInstagram !== undefined) params.has_instagram = hasInstagram
    const res = await contactsApi.exportCsv(params)
    const blob = new Blob([res.data], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'contacts.csv'
    a.click()
    URL.revokeObjectURL(url)
  }, [hasEmail, hasInstagram])

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contacts</h1>
          <p className="text-gray-500 mt-0.5">
            {contacts.length} contacts · {table.getFilteredRowModel().rows.length} shown
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Import */}
          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            onChange={handleImport}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Upload className="w-4 h-4" />
            {importMutation.isPending ? 'Importing...' : 'Import CSV'}
          </button>

          {/* Export */}
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {/* Title search */}
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Filter by title..."
            value={titleFilter}
            onChange={(e) => setTitleFilter(e.target.value)}
            className="pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 w-48"
          />
        </div>

        {/* Has Email */}
        <select
          value={hasEmail === undefined ? '' : String(hasEmail)}
          onChange={(e) => setHasEmail(e.target.value === '' ? undefined : e.target.value === 'true')}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">Email: any</option>
          <option value="true">Has email</option>
          <option value="false">No email</option>
        </select>

        {/* Has Instagram */}
        <select
          value={hasInstagram === undefined ? '' : String(hasInstagram)}
          onChange={(e) => setHasInstagram(e.target.value === '' ? undefined : e.target.value === 'true')}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">Instagram: any</option>
          <option value="true">Has Instagram</option>
          <option value="false">No Instagram</option>
        </select>

        {/* Clear filters */}
        {(titleFilter || hasEmail !== undefined || hasInstagram !== undefined) && (
          <button
            onClick={() => {
              setTitleFilter('')
              setHasEmail(undefined)
              setHasInstagram(undefined)
            }}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <X className="w-3.5 h-3.5" />
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-gray-500 py-8">Loading...</div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Users className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No contacts yet.</p>
          <p className="text-sm text-gray-400 mt-1">Import from CSV or run contact discovery on a company.</p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  {table.getHeaderGroups()[0].headers.map((header) => (
                    <th
                      key={header.id}
                      className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-3"
                    >
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedContact(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-gray-500">
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                <ChevronLeft className="w-4 h-4" />
                Prev
              </button>
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {/* Contact Detail Drawer */}
      {selectedContact && (
        <ContactDrawer
          contact={selectedContact}
          onClose={() => setSelectedContact(null)}
        />
      )}
    </div>
  )
}
