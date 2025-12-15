import { useEffect, useState } from 'react'

export default function PaymentSuccess() {
  const [verifying, setVerifying] = useState(true)
  const [error, setError] = useState(null)
  const [sessionData, setSessionData] = useState(null)

  // Parse query params from URL
  const searchParams = new URLSearchParams(window.location.search)
  const sessionId = searchParams.get('session_id')

  useEffect(() => {
    if (!sessionId) {
      setError('No session ID found')
      setVerifying(false)
      return
    }

    verifySession()
  }, [sessionId])

  const verifySession = async () => {
    try {
      const response = await fetch(`/api/payments/verify-session?session_id=${sessionId}`, {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to verify payment')
      }

      const data = await response.json()
      setSessionData(data)
      setVerifying(false)

      // Redirect to audit report after 3 seconds
      const auditId = data.metadata?.audit_id
      if (auditId) {
        setTimeout(() => {
          window.location.href = `/report/${auditId}`
        }, 3000)
      }
    } catch (err) {
      setError('Failed to verify payment. Please contact support.')
      setVerifying(false)
    }
  }

  if (verifying) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mx-auto mb-4 h-16 w-16 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600"></div>
          <p className="text-lg text-gray-600">Verifying payment...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md rounded-2xl border border-red-200 bg-white p-8 text-center shadow-lg">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
            <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="mb-2 text-2xl font-bold text-gray-900">Payment Error</h2>
          <p className="mb-6 text-gray-600">{error}</p>
          <button
            onClick={() => window.location.href = '/'}
            className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700"
          >
            Return to Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 text-center shadow-lg">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h2 className="mb-2 text-2xl font-bold text-gray-900">Payment Successful!</h2>
        <p className="mb-6 text-gray-600">
          Your AI visibility action plan is ready. Redirecting you to the full report...
        </p>

        {sessionData?.amount_total && (
          <div className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <p className="text-sm text-gray-600">Amount paid</p>
            <p className="text-2xl font-bold text-gray-900">
              ${(sessionData.amount_total / 100).toFixed(2)}
            </p>
          </div>
        )}

        <button
          onClick={() => {
            const auditId = sessionData?.metadata?.audit_id
            if (auditId) {
              window.location.href = `/report/${auditId}`
            } else {
              window.location.href = '/'
            }
          }}
          className="w-full rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 font-bold text-white transition-all hover:from-blue-700 hover:to-purple-700 shadow-md"
        >
          See Your Complete Audit
        </button>
      </div>
    </div>
  )
}
