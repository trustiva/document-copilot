import { Navigate, Outlet } from 'react-router-dom'
import { useSession } from '@/lib/useSession'

export default function RequireAuth() {
  const { session, loading } = useSession()
  if (loading) return <p className="p-8 text-gray-500">Loading...</p>
  if (!session) return <Navigate to="/login" replace />
  return <Outlet />
}
