import { useCallback, useEffect, useState } from 'react'
import ChatPane from '@/components/chat/ChatPane'
import PassageInspector from '@/components/chat/PassageInspector'
import ThreadSidebar from '@/components/chat/ThreadSidebar'
import { api, type Company, type Message, type SourcePassage, type Thread } from '@/lib/api'
import { supabase } from '@/lib/supabase'

export default function HomePage() {
  const [health, setHealth] = useState<string | null>(null)
  const [user, setUser] = useState<{ id: string; email: string } | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeThread, setActiveThread] = useState<Thread | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activePassage, setActivePassage] = useState<{
    passage: SourcePassage
    quote?: string | null
  } | null>(null)

  const fetchThreads = useCallback(() => {
    return api.threads
      .list()
      .then(setThreads)
      .catch((e: unknown) => console.error('Failed to load threads', e))
  }, [])

  useEffect(() => {
    api
      .get<{ status: string }>('/health')
      .then((data) => setHealth(data.status))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Backend unreachable'),
      )

    api
      .get<{ id: string; email: string }>('/me')
      .then((data) => setUser(data))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Failed to fetch user profile'),
      )

    api
      .get<Company[]>('/companies')
      .then((data) => setCompanies(data))
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Failed to fetch companies'),
      )

    api.threads
      .list()
      .then(setThreads)
      .catch((e: unknown) => console.error('Failed to load threads', e))
      .finally(() => setLoadingThreads(false))
  }, [])

  async function handleSelectThread(thread: Thread) {
    setActiveThread(thread)
    try {
      const msgs = await api.threads.listMessages(thread.id)
      setMessages(msgs)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load thread messages')
    }
  }

  async function handleNewThread(initialPrompt?: string) {
    try {
      const newThread = await api.threads.create(
        initialPrompt ? initialPrompt.slice(0, 30) : 'New Research Chat',
      )
      setThreads((prev) => [newThread, ...prev])
      setActiveThread(newThread)
      setMessages([])

      if (initialPrompt) {
        await handleSendMessage(initialPrompt, newThread.id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create thread')
    }
  }

  async function handleDeleteThread(threadId: string) {
    try {
      await api.threads.delete(threadId)
      setThreads((prev) => prev.filter((t) => t.id !== threadId))
      if (activeThread?.id === threadId) {
        setActiveThread(null)
        setMessages([])
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete thread')
    }
  }

  async function handleSendMessage(content: string, threadIdOverride?: string) {
    const threadId = threadIdOverride || activeThread?.id
    if (!threadId) return

    setSending(true)

    // 1. Optimistic user message
    const userMsg: Message = {
      id: crypto.randomUUID(),
      thread_id: threadId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      citations: [],
    }

    // 2. Placeholder assistant message with live streaming state
    const assistantPlaceholderId = crypto.randomUUID()
    const assistantPlaceholder: Message = {
      id: assistantPlaceholderId,
      thread_id: threadId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      citations: [],
      isStreaming: true,
    }

    const updatedHistory = [...messages, userMsg]
    setMessages([...updatedHistory, assistantPlaceholder])

    try {
      // 3. Initiate real-time SSE stream
      await api.threads.stream(
        threadId,
        updatedHistory.map((m) => ({ role: m.role, content: m.content })),
        {
          onTextDelta: (delta: string) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantPlaceholderId
                  ? { ...m, content: m.content + delta }
                  : m,
              ),
            )
          },
          onCitations: (citations, citedPassages) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantPlaceholderId
                  ? { ...m, citations, cited_passages: citedPassages }
                  : m,
              ),
            )
          },
          onDone: ({ message_id }) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantPlaceholderId
                  ? { ...m, id: message_id, isStreaming: false }
                  : m,
              ),
            )
            fetchThreads()
          },
          onError: (errMsg: string) => {
            setError(errMsg)
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantPlaceholderId
                  ? {
                      ...m,
                      content:
                        m.content ||
                        'Error: could not generate grounded response from SEC filings.',
                      isStreaming: false,
                    }
                  : m,
              ),
            )
          },
        },
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Streaming chat request failed')
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantPlaceholderId
            ? {
                ...m,
                content: m.content || 'Failed to complete chat stream.',
                isStreaming: false,
              }
            : m,
        ),
      )
    } finally {
      setSending(false)
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut()
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
      {/* Top Navigation Bar */}
      <header className="h-20 border-b border-gray-200 bg-white px-6 flex items-center justify-between shrink-0 shadow-2xs">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Document Copilot
            </h1>
            <span className="text-xs text-gray-500 font-medium">
              Driftwood Capital Research Platform
            </span>
          </div>
          {health && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-200 shadow-2xs">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              SEC Corpus Online
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="text-right">
              <p className="text-sm font-semibold text-gray-900">{user.email}</p>
              <p className="text-xs text-gray-400">Equity Research Analyst</p>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="rounded-lg border border-gray-300 bg-white px-3.5 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors shadow-2xs cursor-pointer"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: User Research Threads */}
        <ThreadSidebar
          threads={threads}
          activeThreadId={activeThread?.id || null}
          onSelectThread={handleSelectThread}
          onNewThread={() => handleNewThread()}
          onDeleteThread={handleDeleteThread}
          loading={loadingThreads}
        />

        {/* Right: Active Chat or Dashboard Explorer */}
        <ChatPane
          activeThread={activeThread}
          messages={messages}
          onSendMessage={handleSendMessage}
          sending={sending}
          companies={companies}
          onSelectCompanyPrompt={(prompt) => handleNewThread(prompt)}
          onInspectPassage={(passage, quote) => setActivePassage({ passage, quote })}
        />
      </div>

      {/* Slide-out Passage Inspector Modal */}
      <PassageInspector
        passage={activePassage?.passage ?? null}
        activeQuote={activePassage?.quote}
        onClose={() => setActivePassage(null)}
      />

      {error && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white text-xs px-4 py-3 rounded-xl shadow-xl flex items-center gap-3 z-50 animate-bounce">
          <span className="font-medium">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-2 font-bold hover:opacity-80 p-1"
            title="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  )
}
