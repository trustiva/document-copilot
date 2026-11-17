import { useState } from 'react'
import type { Message, SourcePassage, Thread } from '@/lib/api'
import CompanyList, { type Company } from '@/components/CompanyList'
import MessageContent from './MessageContent'

interface ChatPaneProps {
  activeThread: Thread | null
  messages: Message[]
  onSendMessage: (content: string) => Promise<void>
  sending: boolean
  companies: Company[]
  onSelectCompanyPrompt?: (prompt: string) => void
  onInspectPassage?: (passage: SourcePassage, quote?: string | null) => void
}

export default function ChatPane({
  activeThread,
  messages,
  onSendMessage,
  sending,
  companies,
  onSelectCompanyPrompt,
  onInspectPassage,
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
                `Across ${c.name}'s (${c.ticker}) latest 10-K filings, how did the primary revenue streams and segment profitability change?`
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
      <div className="border-b border-gray-200 px-6 py-3.5 flex items-center justify-between bg-white">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-gray-900 text-sm">{activeThread.title}</h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              Grounded AI
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Started on {new Date(activeThread.created_at).toLocaleDateString()}
          </p>
        </div>

        <div className="text-xs text-gray-400 font-mono">
          Corpus: SEC 10-K (2021–2026)
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {messages.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">
            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3 text-gray-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
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
                  className={`max-w-3xl rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-xs ${
                    isUser
                      ? 'bg-black text-white rounded-br-xs'
                      : 'bg-gray-50/90 text-gray-900 rounded-bl-xs border border-gray-200/80'
                  }`}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  ) : (
                    <MessageContent content={m.content} isStreaming={m.isStreaming} />
                  )}

                  {/* Interactive Verified Citations Shelf */}
                  {m.citations && m.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-gray-200 text-xs">
                      <div className="flex items-center gap-1.5 text-gray-500 font-semibold mb-2">
                        <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Verified Citations ({m.citations.length})</span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {m.citations.map((c, cIdx) => {
                          const passage =
                            c.passage ||
                            m.cited_passages?.find((p) => p.chunk_id === c.chunk_id)

                          const badgeText = passage
                            ? `${passage.ticker} ${passage.form} (Chunk #${passage.chunk_index})`
                            : `Filing Chunk [${c.chunk_id.slice(0, 8)}]`

                          return (
                            <button
                              key={cIdx}
                              type="button"
                              onClick={() => {
                                if (passage && onInspectPassage) {
                                  onInspectPassage(passage, c.quote)
                                }
                              }}
                              className={`group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                                passage
                                  ? 'bg-white border border-gray-300 text-gray-800 hover:border-black hover:bg-gray-100 hover:shadow-xs cursor-pointer'
                                  : 'bg-gray-100 text-gray-500 cursor-default'
                              }`}
                              title={c.quote ? `Quote: "${c.quote}"` : 'Click to inspect underlying passage'}
                            >
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              <span className="font-semibold">{badgeText}</span>
                              {passage && (
                                <svg
                                  className="w-3 h-3 text-gray-400 group-hover:text-black transition-colors"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                              )}
                            </button>
                          )
                        })}
                      </div>
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

      {/* Input Form & Quick Prompt suggestions */}
      <div className="border-t border-gray-200 p-4 bg-gray-50/70">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask an SEC filing research question (e.g. Compare Apple iPhone vs Services revenue mix)..."
            className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-black shadow-xs transition-shadow"
            disabled={sending}
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="rounded-lg bg-black px-5 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
          >
            {sending ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Analyzing...</span>
              </>
            ) : (
              <span>Send</span>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
