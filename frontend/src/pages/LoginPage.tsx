import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'

export default function LoginPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  async function submit(mode: 'signIn' | 'signUp', form: HTMLFormElement) {
    const data = new FormData(form)
    const email = String(data.get('email'))
    const password = String(data.get('password'))

    const { error } =
      mode === 'signIn'
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password })

    if (error) setError(error.message)
    else navigate('/')
  }

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="text-2xl font-bold">Sign in</h1>
      <form
        className="mt-6 flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          submit('signIn', e.currentTarget)
        }}
      >
        <input name="email" type="email" required placeholder="Email"
          className="rounded border p-2" />
        <input name="password" type="password" required minLength={6}
          placeholder="Password" className="rounded border p-2" />
        <button type="submit" className="rounded bg-black p-2 text-white">
          Sign in
        </button>
        <button
          type="button"
          className="rounded border p-2"
          onClick={(e) => submit('signUp', e.currentTarget.form!)}
        >
          Create account
        </button>
        {error && <p className="text-red-600">{error}</p>}
      </form>
    </main>
  )
}
