import { useEffect, useState } from 'react'
import { api, type Company, type Message, type Thread } from '@/lib/api'
import { supabase } from '@/lib/supabase'
import ChatPane from '@/components/chat/ChatPane'
import ThreadSidebar from '@/components/chat/ThreadSidebar'

type Health = { status: string }
type User = { id: string; email: string }

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeThread, setActiveThread] = useState<Thread | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchThreads = async () => {
    try {
      const data = await api.threads.list()
      setThreads(data)
    } catch (e) {
      console.error('Failed to load threads', e)
    } finally {
      setLoadingThreads(false)
    }
  }

  useEffect(() => {
    api
      .get<Health>('/health')
      .then(setHealth)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Unknown error'),
      )

    api
      .get<User>('/me')
      .then(setUser)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Auth error'),
      )

    api
      .get<Company[]>('/companies')
      .then(setCompanies)
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
        initialPrompt ? initialPrompt.slice(0, 30) : 'New Research Chat'
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
    try {
      const sentMessage = await api.threads.sendMessage(threadId, content)
      setMessages((prev) => [...prev, sentMessage])
      // Refresh threads to update latest modified title/timestamp
      fetchThreads()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message')
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
      <header className="h-20 border-b border-gray-200 bg-white px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <h1 className="text-xl font-bold tracking-tight text-gray-900">
              Document Copilot
            </h1>
            <span className="text-xs text-gray-500">
              Driftwood Capital Research Platform
            </span>
          </div>
          {health && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
              API Online
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{user.email}</p>
              <p className="text-xs text-gray-400">Equity Research Analyst</p>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
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
        />
      </div>

      {error && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white text-xs px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-2 font-bold">
            ×
          </button>
        </div>
      )}
    </div>
  )
}
