import { Component, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './context/AuthContext'
import LandingPage from './components/LandingPage'
import AuditStatus from './components/AuditStatus'
import ReportPage from './pages/ReportPage'
import PaymentSuccess from './pages/PaymentSuccess'
import AuthVerify from './pages/AuthVerify'

const queryClient = new QueryClient()

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // eslint-disable-next-line no-console
    console.error('Report UI crashed:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-white">
          <div className="mx-auto max-w-3xl px-4 py-16">
            <div className="rounded-2xl border border-red-200 bg-red-50 p-8 shadow-sm">
              <div className="text-lg font-extrabold text-gray-900">Report UI crashed</div>
              <div className="mt-2 text-sm text-gray-800 whitespace-pre-wrap">
                {String(this.state.error?.message || this.state.error || 'Unknown error')}
              </div>
              <button
                onClick={() => window.location.reload()}
                className="mt-6 rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
              >
                Reload
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  const [currentJobId, setCurrentJobId] = useState(null)

  const pathname = window.location.pathname || '/'
  const reportMatch = pathname.match(/^\/report\/([0-9a-fA-F-]{36})\/?$/)
  const reportJobId = reportMatch?.[1] || null
  const isPaymentSuccess = pathname.startsWith('/payment/success')
  const isAuthVerify = pathname.startsWith('/auth/verify')

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {isAuthVerify ? (
          <AuthVerify />
        ) : isPaymentSuccess ? (
          <PaymentSuccess />
        ) : reportJobId ? (
          <ErrorBoundary>
            <ReportPage jobId={reportJobId} />
          </ErrorBoundary>
        ) : !currentJobId ? (
          <LandingPage onJobCreated={setCurrentJobId} />
        ) : (
          <div className="min-h-screen bg-white">
            <div className="container mx-auto px-4 py-12">
              <AuditStatus jobId={currentJobId} onReset={() => setCurrentJobId(null)} />
            </div>
          </div>
        )}
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
