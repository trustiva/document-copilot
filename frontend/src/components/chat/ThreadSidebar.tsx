import type { Thread } from '@/lib/api'

interface ThreadSidebarProps {
  threads: Thread[]
  activeThreadId: string | null
  onSelectThread: (thread: Thread) => void
  onNewThread: () => void
  onDeleteThread: (threadId: string) => void
  loading?: boolean
}

export default function ThreadSidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  loading,
}: ThreadSidebarProps) {
  return (
    <aside className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col h-[calc(100vh-5rem)]">
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewThread}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 transition-colors"
        >
          <span>+</span>
          <span>New Research Chat</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="px-2 py-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Your Research Threads
        </div>

        {loading && (
          <p className="px-2 py-3 text-xs text-gray-400">Loading threads...</p>
        )}

        {!loading && threads.length === 0 && (
          <p className="px-2 py-3 text-xs text-gray-400">No chats yet. Start one above!</p>
        )}

        {threads.map((thread) => {
          const isActive = thread.id === activeThreadId
          return (
            <div
              key={thread.id}
              onClick={() => onSelectThread(thread)}
              className={`group flex items-center justify-between rounded-md px-3 py-2 text-sm cursor-pointer transition-colors ${
                isActive
                  ? 'bg-white font-medium text-gray-900 shadow-sm border border-gray-200'
                  : 'text-gray-700 hover:bg-gray-200/60'
              }`}
            >
              <span className="truncate flex-1">{thread.title}</span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteThread(thread.id)
                }}
                className="opacity-0 group-hover:opacity-100 ml-2 text-gray-400 hover:text-red-600 transition-opacity p-0.5"
                title="Delete thread"
              >
                ×
              </button>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
