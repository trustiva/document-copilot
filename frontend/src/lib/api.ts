import { request } from './http'

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

export type Citation = {
  id: string
  chunk_id: string
  quote?: string | null
}

export type Message = {
  id: string
  thread_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  citations: Citation[]
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
  },
}
