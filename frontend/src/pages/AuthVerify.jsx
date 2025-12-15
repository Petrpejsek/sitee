import { useEffect, useState } from 'react'

export default function AuthVerify() {
  const [status, setStatus] = useState('verifying')
  const [error, setError] = useState(null)

  useEffect(() => {
    const verifyToken = async () => {
      const params = new URLSearchParams(window.location.search)
      const token = params.get('token')
      const auditId = params.get('audit_id')

      if (!token) {
        setStatus('error')
        setError('No verification token provided')
        return
      }

      try {
        // Call backend to verify magic link - this will set the auth cookie
        let verifyUrl = `/api/auth/verify-magic-link?token=${token}`
        if (auditId) {
          verifyUrl += `&audit_id=${auditId}`
        }

        const response = await fetch(verifyUrl, {
          credentials: 'include'
        })

        if (response.ok) {
          setStatus('success')
          // Redirect to audit report or homepage after short delay
          setTimeout(() => {
            if (auditId) {
              window.location.href = `/report/${auditId}`
            } else {
              window.location.href = '/'
            }
          }, 1500)
        } else {
          const data = await response.json()
          setStatus('error')
          setError(data.detail || 'Verification failed')
        }
      } catch (err) {
        setStatus('error')
        setError('Network error. Please try again.')
      }
    }

    verifyToken()
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="mx-4 w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-lg text-center">
        {status === 'verifying' && (
          <>
            <div className="mb-4 flex justify-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent"></div>
            </div>
            <h2 className="text-xl font-bold text-gray-900">Verifying your link...</h2>
            <p className="mt-2 text-gray-600">Please wait while we log you in.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="mb-4 flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <h2 className="text-xl font-bold text-gray-900">You're logged in!</h2>
            <p className="mt-2 text-gray-600">Redirecting to your audit...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="mb-4 flex justify-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
            </div>
            <h2 className="text-xl font-bold text-gray-900">Verification failed</h2>
            <p className="mt-2 text-gray-600">{error}</p>
            <button
              onClick={() => window.location.href = '/'}
              className="mt-4 rounded-lg bg-gray-900 px-6 py-2 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Go to homepage
            </button>
          </>
        )}
      </div>
    </div>
  )
}
