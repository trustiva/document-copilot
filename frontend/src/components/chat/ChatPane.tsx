import { useState } from 'react'
import type { Message, Thread } from '@/lib/api'
import CompanyList, { type Company } from '@/components/CompanyList'

interface ChatPaneProps {
  activeThread: Thread | null
  messages: Message[]
  onSendMessage: (content: string) => Promise<void>
  sending: boolean
  companies: Company[]
  onSelectCompanyPrompt?: (prompt: string) => void
}

export default function ChatPane({
  activeThread,
  messages,
  onSendMessage,
  sending,
  companies,
  onSelectCompanyPrompt,
}: ChatPaneProps) {
  const [input, setInput] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || sending) return
    const text = input
    setInput('')
    await onSendMessage(text)
  }

  if (!activeThread) {
    return (
      <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto">
        <div className="text-center py-6">
          <h2 className="text-2xl font-bold text-gray-900">Driftwood Capital Research Copilot</h2>
          <p className="mt-2 text-sm text-gray-600 max-w-lg mx-auto">
            Query SEC 10-K & 10-Q filings with grounded citations. Select or start a research thread on the left, or click a tracked company below to begin.
          </p>
        </div>

        <div className="mt-6">
          <CompanyList
            companies={companies}
            onSelect={(c) => {
              onSelectCompanyPrompt?.(
                `Compare ${c.name} (${c.ticker}) latest 10-K revenue mix and risk factors against previous fiscal years.`
              )
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-5rem)] bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-gray-900">{activeThread.title}</h2>
          <p className="text-xs text-gray-500">
            Started on {new Date(activeThread.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">
            No messages in this research thread yet. Ask an analyst question below!
          </div>
        ) : (
          messages.map((m) => {
            const isUser = m.role === 'user'
            return (
              <div
                key={m.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    isUser
                      ? 'bg-black text-white rounded-br-none'
                      : 'bg-gray-100 text-gray-900 rounded-bl-none border border-gray-200'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>

                  {/* Citations if available */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-gray-200/60 text-xs text-gray-600">
                      <span className="font-semibold block mb-1">Sources Cited:</span>
                      <ul className="list-disc pl-4 space-y-0.5">
                        {m.citations.map((c) => (
                          <li key={c.id}>
                            Chunk {c.chunk_id.slice(0, 8)}...
                            {c.quote && <span className="italic ml-1">"{c.quote}"</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <span className="text-[10px] text-gray-400 mt-1 px-1">
                  {new Date(m.created_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            )
          })
        )}
      </div>

      {/* Input Form */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-gray-200 p-4 bg-gray-50 flex gap-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about 10-K filings (e.g. Apple revenue mix changes)..."
          className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
          disabled={sending}
        />
        <button
          type="submit"
          disabled={!input.trim() || sending}
          className="rounded-lg bg-black px-5 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}
