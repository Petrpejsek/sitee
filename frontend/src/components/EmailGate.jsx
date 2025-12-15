import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function EmailGate({ auditId, onSuccess }) {
  const { requestMagicLink } = useAuth()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const [devMagicLink, setDevMagicLink] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const result = await requestMagicLink(email, auditId)
      setSuccess(true)
      // In dev mode, API returns magic_link directly
      if (result?.magic_link) {
        setDevMagicLink(result.magic_link)
      }
      // Don't call onSuccess yet - wait for user to verify via link
    } catch (err) {
      setError('Failed to send magic link. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="mx-4 w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-2xl">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" />
            </svg>
          </div>
          <h3 className="mb-2 text-2xl font-bold text-gray-900">Check your email</h3>
          <p className="mb-6 text-gray-600">
            We've sent a magic link to <span className="font-semibold">{email}</span>. Click the link in your email to access your full audit.
          </p>
          
          {/* DEV MODE: Show magic link directly */}
          {devMagicLink && (
            <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs font-bold text-yellow-800 mb-2">🔧 DEV MODE - Click to verify:</p>
              <a 
                href={devMagicLink}
                className="text-sm text-blue-600 hover:text-blue-800 underline break-all"
              >
                {devMagicLink}
              </a>
            </div>
          )}
          
          <p className="text-sm text-gray-500">
            The link will expire in 15 minutes. Didn't receive it? Check your spam folder.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-2xl">
        <div className="mb-6">
          <h2 className="mb-2 text-2xl font-bold text-gray-900">Get Full Audit Report</h2>
          <p className="text-gray-600">
            Enter your email to receive a magic link and access the complete audit with detailed recommendations.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-gray-700 mb-2">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Sending...' : 'Send Magic Link'}
          </button>
        </form>

        <p className="mt-4 text-xs text-gray-500 text-center">
          We'll send you a secure login link. No password needed.
        </p>
      </div>
    </div>
  )
}
