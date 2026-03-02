import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { sessionsApi, api, jobsApi } from '../lib/api'
import { Send, Bot, User, Search, MapPin, Users, Briefcase, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  metadata?: Record<string, unknown>
}

interface SearchConfig {
  industries?: string[]
  geographies?: Array<{ city?: string; state?: string; metro?: string }>
  target_roles?: string[]
  min_ig_followers?: number
  min_yelp_reviews?: number
  services_include?: string[]
  max_results_per_geo?: number
}

interface JobStatus {
  id: string
  status: string
  job_type: string
  created_at: string
  completed_at?: string
}

function SearchConfigCard({
  config,
  jobId,
  onLaunch,
  launching,
}: {
  config: SearchConfig | null
  jobId: string | null
  onLaunch: () => void
  launching: boolean
}) {
  const { data: jobData } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
    refetchInterval: jobId ? 3000 : false,
  })

  const job: JobStatus | undefined = jobData?.data

  if (!config) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8 text-gray-400">
        <Search className="w-12 h-12 mb-4 text-gray-200" />
        <p className="text-sm font-medium text-gray-500">Search Config</p>
        <p className="text-xs mt-2 text-gray-400">
          Chat with the assistant to define your prospect search. A preview will appear here
          once the config is ready.
        </p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-5">
      <div>
        <h3 className="font-semibold text-gray-900 text-sm mb-1">Search Configuration</h3>
        <p className="text-xs text-gray-500">Ready to launch discovery</p>
      </div>

      {config.industries && config.industries.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Briefcase className="w-4 h-4 text-brand-500" />
            <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">Industries</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {config.industries.map((ind) => (
              <span key={ind} className="px-2.5 py-1 bg-brand-50 text-brand-700 rounded-full text-xs font-medium capitalize">
                {ind.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {config.geographies && config.geographies.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="w-4 h-4 text-brand-500" />
            <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">Geographies</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {config.geographies.map((geo, i) => {
              const label = [geo.city, geo.state].filter(Boolean).join(', ') || geo.metro || 'Unknown'
              return (
                <span key={i} className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                  {label}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {config.target_roles && config.target_roles.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-brand-500" />
            <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">Target Roles</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {config.target_roles.map((role) => (
              <span key={role} className="px-2.5 py-1 bg-purple-50 text-purple-700 rounded-full text-xs font-medium capitalize">
                {role.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {(config.min_ig_followers || config.min_yelp_reviews) && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">Filters</span>
          </div>
          <div className="space-y-1 text-xs text-gray-600">
            {config.min_ig_followers && (
              <div>Min IG followers: <span className="font-medium">{config.min_ig_followers.toLocaleString()}</span></div>
            )}
            {config.min_yelp_reviews && (
              <div>Min Yelp reviews: <span className="font-medium">{config.min_yelp_reviews}</span></div>
            )}
            {config.max_results_per_geo && (
              <div>Max results per geo: <span className="font-medium">{config.max_results_per_geo}</span></div>
            )}
          </div>
        </div>
      )}

      {config.services_include && config.services_include.length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-700 uppercase tracking-wide mb-2">Services</div>
          <div className="flex flex-wrap gap-1.5">
            {config.services_include.map((svc) => (
              <span key={svc} className="px-2.5 py-1 bg-green-50 text-green-700 rounded-full text-xs font-medium capitalize">
                {svc}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Job status */}
      {job && (
        <div className={`rounded-lg p-3 text-xs flex items-center gap-2 ${
          job.status === 'queued' || job.status === 'running'
            ? 'bg-amber-50 text-amber-700'
            : job.status === 'complete'
            ? 'bg-green-50 text-green-700'
            : 'bg-red-50 text-red-700'
        }`}>
          {job.status === 'running' || job.status === 'queued' ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : job.status === 'complete' ? (
            <CheckCircle className="w-3.5 h-3.5" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5" />
          )}
          <span className="font-medium capitalize">
            Discovery {job.status === 'queued' ? 'queued' : job.status === 'running' ? 'running…' : job.status}
          </span>
        </div>
      )}

      <button
        onClick={onLaunch}
        disabled={launching || (job?.status === 'running' || job?.status === 'queued')}
        className="w-full py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
      >
        {launching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        {launching ? 'Launching…' : 'Launch Search'}
      </button>
    </div>
  )
}

export function ChatSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [searchConfig, setSearchConfig] = useState<SearchConfig | null>(null)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [launching, setLaunching] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data: sessionData } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
  })

  const { data: historyData } = useQuery({
    queryKey: ['chat-history', sessionId],
    queryFn: () => api.get(`/chat/history/${sessionId}`),
    enabled: !!sessionId,
  })

  useEffect(() => {
    if (historyData?.data) {
      const msgs: Message[] = historyData.data
      setMessages(msgs)
      // Restore search_config from last assistant message that has one
      for (let i = msgs.length - 1; i >= 0; i--) {
        const m = msgs[i]
        if (m.role === 'assistant' && m.metadata?.triggered_search_config) {
          setSearchConfig(m.metadata.triggered_search_config as SearchConfig)
          if (m.metadata.job_id) setActiveJobId(m.metadata.job_id as string)
          break
        }
      }
    }
  }, [historyData])

  // Also load search_config from session
  useEffect(() => {
    if (sessionData?.data?.search_config && !searchConfig) {
      setSearchConfig(sessionData.data.search_config)
    }
  }, [sessionData, searchConfig])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return
    const userText = input.trim()
    setInput('')

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userText,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setIsStreaming(true)
    setStreamingContent('')

    const token = localStorage.getItem('access_token')
    const url = `${BASE_URL}/chat`

    let fullText = ''

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: sessionId, message: userText }),
      })

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const event = JSON.parse(raw)
            if (event.type === 'token') {
              fullText += event.text
              setStreamingContent(fullText)
            } else if (event.type === 'done') {
              const finalMsg: Message = {
                id: event.message_id,
                role: 'assistant',
                content: fullText,
                created_at: new Date().toISOString(),
                metadata: event.search_config
                  ? { triggered_search_config: event.search_config, job_id: event.job_id }
                  : undefined,
              }
              setMessages((prev) => [...prev, finalMsg])
              setStreamingContent('')

              if (event.search_config) {
                setSearchConfig(event.search_config)
                if (event.job_id) setActiveJobId(event.job_id)
                queryClient.invalidateQueries({ queryKey: ['session', sessionId] })
              }
            } else if (event.type === 'error') {
              console.error('SSE error:', event.message)
              setMessages((prev) => [
                ...prev,
                {
                  id: Date.now().toString(),
                  role: 'assistant',
                  content: `⚠️ Error: ${event.message}`,
                  created_at: new Date().toISOString(),
                },
              ])
              setStreamingContent('')
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      console.error('Stream error:', err)
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: '⚠️ Failed to connect to assistant. Please try again.',
          created_at: new Date().toISOString(),
        },
      ])
      setStreamingContent('')
    } finally {
      setIsStreaming(false)
    }
  }, [input, isStreaming, sessionId, queryClient])

  const handleLaunchSearch = async () => {
    if (!searchConfig || !sessionId) return
    setLaunching(true)
    try {
      const resp = await api.post('/companies/search', {
        session_id: sessionId,
        search_config: searchConfig,
      })
      if (resp.data?.job_id) {
        setActiveJobId(resp.data.job_id)
      }
    } catch (err) {
      console.error('Launch search error:', err)
    } finally {
      setLaunching(false)
    }
  }

  const session = sessionData?.data

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Chat panel */}
      <div className="flex flex-col flex-1 min-w-0 border-r border-gray-200">
        {/* Header */}
        <div className="border-b border-gray-200 bg-white px-6 py-4 flex-shrink-0">
          <h1 className="font-semibold text-gray-900">{session?.name || 'Research Session'}</h1>
          <p className="text-xs text-gray-500 mt-0.5">AI Prospecting Assistant</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center py-12">
              <Bot className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm max-w-md mx-auto">
                I'm your B2B prospecting assistant. Tell me what cities and types of providers
                you're looking for, and I'll help you build a targeted search.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                msg.role === 'user' ? 'bg-brand-100' : 'bg-gray-100'
              }`}>
                {msg.role === 'user'
                  ? <User className="w-4 h-4 text-brand-600" />
                  : <Bot className="w-4 h-4 text-gray-600" />}
              </div>
              <div className={`max-w-2xl px-4 py-3 rounded-xl text-sm ${
                msg.role === 'user'
                  ? 'bg-brand-500 text-white rounded-tr-none'
                  : 'bg-white border border-gray-200 rounded-tl-none'
              }`}>
                {msg.role === 'assistant' ? (
                  <ReactMarkdown className="prose prose-sm max-w-none">{msg.content}</ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))}

          {/* Streaming in-progress */}
          {isStreaming && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-gray-600" />
              </div>
              <div className="max-w-2xl px-4 py-3 bg-white border border-gray-200 rounded-xl rounded-tl-none text-sm">
                {streamingContent ? (
                  <ReactMarkdown className="prose prose-sm max-w-none">{streamingContent}</ReactMarkdown>
                ) : (
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-4 flex-shrink-0">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="Tell me what you're looking for..."
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              disabled={isStreaming}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              className="px-4 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-xl transition-colors"
            >
              {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Right: Search config panel */}
      <div className="w-80 flex-shrink-0 bg-white overflow-y-auto">
        <SearchConfigCard
          config={searchConfig}
          jobId={activeJobId}
          onLaunch={handleLaunchSearch}
          launching={launching}
        />
      </div>
    </div>
  )
}
