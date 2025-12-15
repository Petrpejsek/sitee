import { useState, useEffect } from 'react'

// Helper: normalize domain
const normalizeDomain = (input) => {
  return input
    .trim()
    .replace(/^https?:\/\//, '')  // Remove http(s)://
    .replace(/^www\./, '')         // Remove www.
    .replace(/\/.*$/, '')          // Remove path
    .toLowerCase()
}

export default function AuditForm({ onJobCreated, initialDomain = '' }) {
  const [domain, setDomain] = useState(initialDomain)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Update domain if initialDomain changes (from hero input)
  useEffect(() => {
    if (initialDomain) {
      setDomain(initialDomain)
    }
  }, [initialDomain])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const normalizedDomain = normalizeDomain(domain)
      
      if (!normalizedDomain) {
        throw new Error('Please enter a valid domain')
      }
      
      const response = await fetch('/api/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_domain: normalizedDomain }),
      })

      if (!response.ok) {
        throw new Error('Failed to create audit job')
      }

      const data = await response.json()
      onJobCreated(data.id)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl shadow-xl p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Get Your Free AI Visibility Audit
        </h2>
        <p className="text-gray-600 mb-6">
          See how AI systems like ChatGPT understand your business
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Single Domain Input */}
          <div>
            <input
              type="text"
              required
              placeholder="yourwebsite.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              disabled={loading}
              className="w-full px-5 py-4 text-lg border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <p className="mt-2 text-sm text-gray-500">
              Without https:// • Free • No credit card • Results in ~5 minutes
            </p>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold py-4 px-8 rounded-xl hover:shadow-xl hover:scale-[1.02] disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200"
          >
            {loading ? 'Analyzing Your Website...' : 'Get Your Free AI Visibility Audit'}
          </button>
        </form>
      </div>
    </div>
  )
}


