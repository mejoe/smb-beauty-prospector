import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { companiesApi, contactsApi, outreachApi } from '../lib/api'
import { Building2, Users, Instagram, Send, Plus, ArrowRight } from 'lucide-react'

function StatCard({ label, value, icon: Icon, color }: {
  label: string
  value: number | string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
    </div>
  )
}

export function Dashboard() {
  const { user } = useAuth()

  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list({ limit: 1 }),
  })

  const { data: contacts } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => contactsApi.list({ limit: 1 }),
  })

  const { data: contactsWithIG } = useQuery({
    queryKey: ['contacts', { has_instagram: true }],
    queryFn: () => contactsApi.list({ has_instagram: true, limit: 1 }),
  })

  const { data: campaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => outreachApi.listCampaigns(),
  })

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back{user?.name ? `, ${user.name.split(' ')[0]}` : ''}!
        </h1>
        <p className="text-gray-500 mt-1">Here's your prospecting overview</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Companies"
          value={Array.isArray(companies?.data) ? companies.data.length : '—'}
          icon={Building2}
          color="bg-blue-500"
        />
        <StatCard
          label="Contacts"
          value={Array.isArray(contacts?.data) ? contacts.data.length : '—'}
          icon={Users}
          color="bg-green-500"
        />
        <StatCard
          label="With Instagram"
          value={Array.isArray(contactsWithIG?.data) ? contactsWithIG.data.length : '—'}
          icon={Instagram}
          color="bg-pink-500"
        />
        <StatCard
          label="Campaigns"
          value={Array.isArray(campaigns?.data) ? campaigns.data.length : '—'}
          icon={Send}
          color="bg-purple-500"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              to="/sessions"
              className="flex items-center justify-between p-3 bg-gray-50 hover:bg-brand-50 rounded-lg group transition-colors"
            >
              <div className="flex items-center gap-3">
                <Plus className="w-4 h-4 text-gray-500 group-hover:text-brand-500" />
                <span className="text-sm font-medium text-gray-700 group-hover:text-brand-700">
                  New Research Session
                </span>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-500" />
            </Link>
            <Link
              to="/outreach"
              className="flex items-center justify-between p-3 bg-gray-50 hover:bg-brand-50 rounded-lg group transition-colors"
            >
              <div className="flex items-center gap-3">
                <Send className="w-4 h-4 text-gray-500 group-hover:text-brand-500" />
                <span className="text-sm font-medium text-gray-700 group-hover:text-brand-700">
                  New Outreach Campaign
                </span>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-500" />
            </Link>
            <Link
              to="/contacts"
              className="flex items-center justify-between p-3 bg-gray-50 hover:bg-brand-50 rounded-lg group transition-colors"
            >
              <div className="flex items-center gap-3">
                <Users className="w-4 h-4 text-gray-500 group-hover:text-brand-500" />
                <span className="text-sm font-medium text-gray-700 group-hover:text-brand-700">
                  Browse Contacts
                </span>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-500" />
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Platform Status</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Instagram Account</span>
              <span className={`font-medium ${user?.ig_session_valid ? 'text-green-600' : 'text-red-500'}`}>
                {user?.ig_session_valid ? `Connected (${user.ig_username})` : 'Not connected'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">AI Chat</span>
              <span className="text-green-600 font-medium">Ready</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Enrichment Worker</span>
              <span className="text-yellow-600 font-medium">Sprint 5</span>
            </div>
          </div>
          <Link
            to="/settings"
            className="inline-flex items-center gap-2 mt-4 text-sm text-brand-600 hover:underline font-medium"
          >
            Go to Settings <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  )
}
