import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

type Health = { status: string }

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<Health>('/health')
      .then(setHealth)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Unknown error'),
      )
  }, [])

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-2xl font-bold">Document Copilot</h1>
      {error && <p className="mt-4 text-red-600">Error: {error}</p>}
      {health && <p className="mt-4 text-green-700">Backend: {health.status}</p>}
      {!error && !health && <p className="mt-4 text-gray-500">Loading...</p>}
    </main>
  )
}
