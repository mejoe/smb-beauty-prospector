import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { sessionsApi, api } from '../lib/api'
import { Send, Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export function ChatSession() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

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
      setMessages(historyData.data)
    }
  }, [historyData])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMutation = useMutation({
    mutationFn: async (message: string) => {
      const resp = await api.post('/chat', {
        session_id: sessionId,
        message,
      })
      return resp.data
    },
    onMutate: (message) => {
      const tempMsg: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempMsg])
    },
    onSuccess: (data) => {
      const assistantMsg: Message = {
        id: data.message_id,
        role: 'assistant',
        content: data.reply,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    },
  })

  const handleSend = () => {
    if (!input.trim() || sendMutation.isPending) return
    const msg = input.trim()
    setInput('')
    sendMutation.mutate(msg)
  }

  const session = sessionData?.data

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="font-semibold text-gray-900">{session?.name || 'Research Session'}</h1>
        <p className="text-xs text-gray-500 mt-0.5">AI Prospecting Assistant</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
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
              {msg.role === 'user' ? <User className="w-4 h-4 text-brand-600" /> : <Bot className="w-4 h-4 text-gray-600" />}
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
        {sendMutation.isPending && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-600" />
            </div>
            <div className="px-4 py-3 bg-white border border-gray-200 rounded-xl rounded-tl-none">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Tell me what you're looking for..."
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sendMutation.isPending}
            className="px-4 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-xl transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
