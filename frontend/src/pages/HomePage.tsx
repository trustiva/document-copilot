import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { supabase } from '@/lib/supabase'
import CompanyList, { type Company } from '@/components/CompanyList'

type Health = { status: string }
type User = { id: string; email: string }

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [error, setError] = useState<string | null>(null)

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
  }, [])

  async function handleSignOut() {
    await supabase.auth.signOut()
  }

  return (
    <main className="mx-auto max-w-xl p-8">
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Copilot</h1>
          {user && (
            <p className="text-sm text-gray-600 mt-1">
              Signed in as <span className="font-medium text-gray-900">{user.email}</span>
            </p>
          )}
        </div>
        <button
          onClick={handleSignOut}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
        >
          Sign out
        </button>
      </div>

      {error && <p className="mt-4 text-sm text-red-600">Error: {error}</p>}
      {health && <p className="mt-4 text-sm text-green-700">Backend: {health.status}</p>}
      {!error && !health && <p className="mt-4 text-sm text-gray-500">Loading...</p>}

      <CompanyList companies={companies} />
    </main>
  )
}
