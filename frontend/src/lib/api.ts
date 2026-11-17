import { env } from './env'
import { request } from './http'
import { supabase } from './supabase'

export type Company = {
  ticker: string
  name: string
  cik?: string
}

export type Thread = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export type SourcePassage = {
  chunk_id: string
  document_id: string
  chunk_index: number
  ticker: string
  form: string
  filing_date: string
  accession_number: string
  source_url: string
  content: string
  score?: number
}

export type Citation = {
  id?: string
  chunk_id: string
  quote?: string | null
  passage?: SourcePassage
}

export type Message = {
  id: string
  thread_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  citations: Citation[]
  cited_passages?: SourcePassage[]
  isStreaming?: boolean
}

export type StreamHandlers = {
  onTextDelta: (delta: string) => void
  onCitations: (citations: Citation[], passages: SourcePassage[]) => void
  onDone: (data: { message_id: string; thread_id: string }) => void
  onError: (error: string) => void
}

export async function streamChat(
  threadId: string,
  messages: { role: 'user' | 'assistant' | 'system'; content: string }[],
  handlers: StreamHandlers,
): Promise<void> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token

  const response = await fetch(`${env.apiBaseUrl}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ threadId, messages }),
  })

  if (!response.ok || !response.body) {
    throw new Error(`Chat stream request failed: ${response.statusText}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    let currentEvent = ''
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) {
        currentEvent = ''
        continue
      }
      if (trimmed.startsWith('event:')) {
        currentEvent = trimmed.replace('event:', '').trim()
      } else if (trimmed.startsWith('data:')) {
        const rawData = trimmed.replace('data:', '').trim()
        try {
          const parsed = JSON.parse(rawData)
          if (currentEvent === 'text' && parsed.delta) {
            handlers.onTextDelta(parsed.delta)
          } else if (currentEvent === 'citations') {
            handlers.onCitations(parsed.citations || [], parsed.cited_passages || [])
          } else if (currentEvent === 'done') {
            handlers.onDone(parsed)
          } else if (currentEvent === 'error') {
            handlers.onError(parsed.error || 'Unknown assistant error')
          }
        } catch (err) {
          console.warn('Failed to parse SSE data line', rawData, err)
        }
      }
    }
  }
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),

  threads: {
    list: () => request<Thread[]>('GET', '/threads'),
    create: (title?: string) => request<Thread>('POST', '/threads', { title }),
    get: (id: string) => request<Thread>('GET', `/threads/${id}`),
    delete: (id: string) => request<void>('DELETE', `/threads/${id}`),
    listMessages: (threadId: string) =>
      request<Message[]>('GET', `/threads/${threadId}/messages`),
    sendMessage: (threadId: string, content: string) =>
      request<Message>('POST', `/threads/${threadId}/messages`, { content }),
    stream: streamChat,
  },
}
