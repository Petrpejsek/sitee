import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

export default function AuditStatus({ jobId, onReset }) {
  // Frontend display step (independent of backend)
  const [displayStep, setDisplayStep] = useState(0)
  const [stepStartTime, setStepStartTime] = useState(Date.now())
  const STEP_DURATION = 30000 // 30 seconds per step

  const { data: job, isLoading, error } = useQuery({
    queryKey: ['audit', jobId],
    queryFn: async () => {
      const response = await fetch(`/api/audit/${jobId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch audit status')
      }
      return response.json()
    },
    refetchInterval: (query) => {
      const data = query.state.data
      // Stop polling if completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 3000 // Poll every 3 seconds
    },
  })

  // Auto-redirect to report when completed
  useEffect(() => {
    if (job?.status === 'completed') {
      // Smooth transition with slight delay
      const timer = setTimeout(() => {
        window.location.href = `/report/${jobId}?access=preview`
      }, 800)
      return () => clearTimeout(timer)
    }
  }, [job?.status, jobId])

  // Initialize displayStep to 1 when job starts
  useEffect(() => {
    if (job && displayStep === 0 && job.status !== 'completed' && job.status !== 'failed') {
      setDisplayStep(1)
      setStepStartTime(Date.now())
    }
  }, [job, displayStep])

  // Frontend timer: Auto-advance steps 1-3 every 30 seconds, step 4 waits for backend
  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed' || displayStep === 0) {
      return
    }

    const backendStep = getActiveStep(job.current_stage)
    
    // If backend is ahead of display, jump forward immediately
    if (backendStep > displayStep) {
      setDisplayStep(backendStep)
      setStepStartTime(Date.now())
      return
    }

    // Auto-advance timer only for steps 1-3 (step 4 waits for real backend completion)
    if (displayStep < 3) {
      const elapsed = Date.now() - stepStartTime
      const remaining = STEP_DURATION - elapsed

      if (remaining <= 0) {
        // Move to next step
        setDisplayStep(prev => prev + 1)
        setStepStartTime(Date.now())
        return
      }

      // Set timer for next step
      const timer = setTimeout(() => {
        setDisplayStep(prev => prev + 1)
        setStepStartTime(Date.now())
      }, remaining)
      return () => clearTimeout(timer)
    }
    // Step 4 just waits for backend to complete (no auto-advance)
  }, [job, displayStep, stepStartTime])

  // Helper function to determine which step is active based on current_stage
  const getActiveStep = (currentStage) => {
    if (!currentStage) return 1
    
    const stageMap = {
      // Step 1: Scanning your website and competitors (both scraping stages together)
      'scraping_target': 1,
      'scraping_competitors': 1,
      
      // Step 2: Preparing AI testing environment
      'preparing_context': 2,
      'building_context': 2,
      'testing_ai_models': 2,
      
      // Step 3: Running AI analysis (longest - the heavy LLM work)
      'identifying_gaps': 3,
      'stage_a_core_audit': 3,
      
      // Step 4: Generating your report (rendering + PDF)
      'rendering_html': 4,
      'generating_pdf': 4,
      'saving_to_database': 4,
    }
    
    return stageMap[currentStage] || 1
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading audit status...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center">
            <div className="text-red-600 text-5xl mb-4">✗</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Error</h2>
            <p className="text-gray-600 mb-6">{error.message}</p>
            <button
              onClick={onReset}
              className="bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-blue-700"
            >
              Create New Audit
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Define steps array (used for both in-progress and completed states)
  const steps = [
    {
      number: 1,
      title: 'Scanning website & competitors',
      description: 'Understanding what you offer',
      icon: '🔍'
    },
    {
      number: 2,
      title: 'Preparing AI testing environment',
      description: 'Building context for AI models',
      icon: '🔬'
    },
    {
      number: 3,
      title: 'Testing AI recommendations',
      description: 'Querying leading AI models',
      icon: '🤖'
    },
    {
      number: 4,
      title: 'Generating your report',
      description: 'Compiling actionable insights',
      icon: '📊'
    }
  ]

  // COMPLETED STATE - Show all steps completed + redirect message
  if (job.status === 'completed') {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-10">
          {/* Main Headline */}
          <div className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 leading-tight">
              Analysis complete for
            </h1>
            <div className="text-4xl md:text-5xl font-bold text-green-600 mb-4 break-all">
              {job.target_domain || 'your website'}
            </div>
            <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto">
              AI recommendations analyzed successfully!
            </p>
          </div>

          {/* All Steps Completed */}
          <div className="mt-8 mb-8 space-y-4">
            {steps.map((step) => (
              <div 
                key={step.number}
                className="flex items-start gap-4 p-5 rounded-xl bg-green-50 border-2 border-green-500 shadow-md"
              >
                {/* Completed Icon */}
                <div className="flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-xl shadow-lg bg-gradient-to-br from-green-500 to-green-600 text-white">
                  <span className="text-2xl">✓</span>
                </div>

                {/* Step Content */}
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-xl text-green-900">
                    {step.title}
                  </div>
                  <div className="text-base mt-1 text-green-700">
                    {step.description}
                  </div>
                  <div className="text-sm text-green-600 font-semibold mt-2">
                    ✓ Completed
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Redirect Message */}
          <div className="text-center py-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-300">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-200 border-t-blue-600 mb-3"></div>
            <div className="text-blue-900 font-bold text-lg">
              Opening your report...
            </div>
            <div className="text-blue-700 text-sm mt-1">
              You'll be redirected automatically
            </div>
          </div>
        </div>
      </div>
    )
  }

  // IN PROGRESS - Progressive reveal design
  if (job.status !== 'completed' && job.status !== 'failed') {
    // Use displayStep (frontend timer) instead of backend stage
    const currentDisplayStep = displayStep || 1

    // Show only steps that are active or completed
    const visibleSteps = steps.filter(step => step.number <= currentDisplayStep)

    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-10">
          {/* Main Headline */}
          <div className="text-center mb-8">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 leading-tight">
              Analyzing how leading AI models recommend
            </h1>
            <div className="text-4xl md:text-5xl font-bold text-blue-600 mb-4 break-all">
              {job.target_domain || 'your website'}
            </div>
            <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto">
              Testing ChatGPT, Claude, Gemini, Perplexity & other leading AI models to see if they understand your business — or recommend competitors instead.
            </p>
          </div>

          {/* Step Progress - Progressive Reveal */}
          <div className="mt-12 mb-10 space-y-4">
            {visibleSteps.length === 0 ? (
              // Initial loader before first step
              <div className="text-center py-20">
                <div className="relative inline-block mb-8">
                  {/* Outer spinning ring */}
                  <div className="animate-spin rounded-full h-32 w-32 border-[10px] border-blue-100 border-t-blue-600 shadow-2xl"></div>
                  {/* Inner pulsing circle */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full opacity-30 animate-ping"></div>
                  </div>
                  {/* Center icon */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-4xl">🤖</span>
                  </div>
                </div>
                <p className="text-3xl font-bold text-gray-900 mb-3">Starting AI Analysis...</p>
                <p className="text-lg text-gray-600 mb-6">Preparing to test leading AI models</p>
                <div className="mt-8 flex justify-center gap-3">
                  <div className="w-5 h-5 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full animate-bounce shadow-xl" style={{animationDelay: '0ms'}}></div>
                  <div className="w-5 h-5 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-full animate-bounce shadow-xl" style={{animationDelay: '200ms'}}></div>
                  <div className="w-5 h-5 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full animate-bounce shadow-xl" style={{animationDelay: '400ms'}}></div>
                </div>
              </div>
            ) : (
              visibleSteps.map((step) => {
                const isCompleted = step.number < currentDisplayStep
                const isActive = step.number === currentDisplayStep

                return (
                  <div 
                    key={step.number}
                    className={`flex items-start gap-4 p-5 rounded-xl transition-all duration-500 transform ${
                      isActive 
                        ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-500 shadow-lg scale-[1.02]' 
                        : 'bg-green-50 border-2 border-green-500 shadow-md'
                    } animate-[slideIn_0.5s_ease-out]`}
                    style={{
                      animation: `slideIn 0.5s ease-out`
                    }}
                  >
                    {/* Step Icon */}
                    <div className={`flex-shrink-0 w-14 h-14 rounded-full flex items-center justify-center font-bold text-xl shadow-lg ${
                      isCompleted 
                        ? 'bg-gradient-to-br from-green-500 to-green-600 text-white' 
                        : 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                    }`}>
                      {isCompleted ? (
                        <span className="text-2xl">✓</span>
                      ) : (
                        <span className="animate-pulse text-2xl">{step.icon}</span>
                      )}
                    </div>

                    {/* Step Content */}
                    <div className="flex-1 min-w-0">
                      <div className={`font-bold text-xl flex items-center gap-3 ${
                        isActive ? 'text-blue-900' : 'text-green-900'
                      }`}>
                        {isActive && (
                          <div className="flex gap-1.5">
                            <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce shadow-lg" style={{animationDelay: '0ms'}}></div>
                            <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce shadow-lg" style={{animationDelay: '150ms'}}></div>
                            <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce shadow-lg" style={{animationDelay: '300ms'}}></div>
                          </div>
                        )}
                        {step.title}
                      </div>
                      <div className={`text-base mt-1 ${
                        isActive ? 'text-blue-700 font-medium' : 'text-green-700'
                      }`}>
                        {step.description}
                      </div>
                      {isCompleted && (
                        <div className="text-sm text-green-600 font-semibold mt-2">
                          ✓ Completed
                        </div>
                      )}
                      {isActive && (
                        <div className="text-sm text-blue-600 font-semibold mt-2">
                          In progress...
                        </div>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Time Expectation */}
          <div className="text-center mt-8 mb-6 py-5 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
            <div className="text-blue-900 font-bold text-lg mb-1">
              ⏱️ This usually takes 2–5 minutes
            </div>
            <div className="text-blue-700 text-base">
              You'll get a clear answer — not guesses.
            </div>
          </div>

          {/* Trust Signals */}
          <div className="border-t pt-6">
            <div className="flex flex-col md:flex-row items-center justify-center gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <span className="text-green-600 text-lg">✓</span>
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-600 text-lg">✓</span>
                <span>Real AI model testing</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-600 text-lg">✓</span>
                <span>Actionable recommendations, not theory</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // COMPLETED or FAILED - Keep existing design
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-600'
      case 'failed':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusEmoji = (status) => {
    switch (status) {
      case 'completed':
        return '✓'
      case 'failed':
        return '✗'
      default:
        return '⏳'
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-2xl shadow-xl p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className={`text-5xl mb-4 ${getStatusColor(job.status)}`}>
            {getStatusEmoji(job.status)}
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            {job.target_domain}
          </h2>
        </div>

        {/* Error Message */}
        {job.status === 'failed' && job.error_message && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm font-semibold text-red-800 mb-1">Error Details:</p>
            <p className="text-sm text-red-700 whitespace-pre-wrap">{job.error_message}</p>
          </div>
        )}

        {/* Scrape Debug Info (for failed jobs) */}
        {job.status === 'failed' && job.scrape_debug && (
          <div className="mb-6">
            <details className="bg-gray-50 rounded-lg">
              <summary className="p-4 cursor-pointer text-sm font-semibold text-gray-700">
                🔍 Debug Details (click to expand)
              </summary>
              <div className="p-4 pt-0 text-xs font-mono space-y-2">
                <div><strong>Input URL:</strong> {job.scrape_debug.input_url}</div>
                <div><strong>Normalized URL:</strong> {job.scrape_debug.normalized_url}</div>
                <div><strong>Final URL:</strong> {job.scrape_debug.final_url || 'N/A'}</div>
                <div><strong>Homepage Status:</strong> {job.scrape_debug.homepage_status_code || 'N/A'}</div>
                <div><strong>Homepage Error:</strong> {job.scrape_debug.homepage_fetch_error || 'None'}</div>
                <div><strong>Blocked Reason:</strong> <span className="text-red-600 font-bold">{job.scrape_debug.blocked_reason || 'unknown'}</span></div>
                <div><strong>Robots.txt Status:</strong> {job.scrape_debug.robots_txt_status || 'N/A'}</div>
                <div><strong>Robots Disallows All:</strong> {job.scrape_debug.robots_disallows_all ? 'YES' : 'No'}</div>
                <div><strong>Sitemap Found:</strong> {job.scrape_debug.sitemap_found ? 'Yes' : 'No'}</div>
                <div><strong>Pages Attempted:</strong> {job.scrape_debug.pages_attempted}</div>
                <div><strong>Pages Success:</strong> {job.scrape_debug.pages_success}</div>
                <div><strong>Pages Failed:</strong> {job.scrape_debug.pages_failed}</div>
                {job.scrape_debug.errors && job.scrape_debug.errors.length > 0 && (
                  <div>
                    <strong>Errors:</strong>
                    <ul className="list-disc ml-4 mt-1">
                      {job.scrape_debug.errors.slice(0, 10).map((err, i) => (
                        <li key={i} className="text-red-600">{err}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          </div>
        )}

        {/* Stats - only show for completed */}
        {job.status === 'completed' && (
          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Pages Scraped</p>
              <p className="text-2xl font-bold text-gray-900">{job.total_pages_scraped}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600 mb-1">Competitors</p>
              <p className="text-2xl font-bold text-gray-900">{job.competitor_domains.length}</p>
            </div>
          </div>
        )}

        {/* Download Buttons */}
        {job.status === 'completed' && (
          <div className="space-y-3 mb-6">
            <div className="mb-2 rounded-lg bg-gray-50 border border-gray-200 p-3">
              <div className="text-xs font-semibold text-gray-600 mb-2">Shareable URL</div>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={`${window.location.origin}/report/${jobId}?access=preview`}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white text-gray-800"
                />
                <button
                  type="button"
                  onClick={async () => {
                    const url = `${window.location.origin}/report/${jobId}?access=preview`
                    try {
                      await navigator.clipboard.writeText(url)
                    } catch (e) {
                      // Fallback: select input for manual copy
                      const el = document.querySelector('input[readonly]')
                      el?.select?.()
                    }
                  }}
                  className="shrink-0 bg-gray-900 text-white font-semibold py-2 px-4 rounded-lg hover:bg-gray-800"
                >
                  Copy
                </button>
              </div>
              <div className="mt-2 text-xs text-gray-500">
                Tip: change access to <span className="font-semibold">free</span> or <span className="font-semibold">paid</span> to preview locking.
              </div>
            </div>
            <a
              href={`/report/${jobId}?access=preview`}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full bg-blue-600 text-white font-semibold py-4 px-6 rounded-lg hover:bg-blue-700 text-center transition-colors duration-200"
            >
              Open Web Dashboard
            </a>
            <a
              href={`/api/audit/${jobId}/json`}
              download
              className="block w-full bg-gray-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-gray-700 text-center transition-colors duration-200"
            >
              Download JSON Data
            </a>
          </div>
        )}

        {/* New Audit Button */}
        <div className="pt-4 border-t">
          <button
            onClick={onReset}
            className="w-full bg-gray-200 text-gray-800 font-semibold py-3 px-6 rounded-lg hover:bg-gray-300 transition-colors duration-200"
          >
            Create New Audit
          </button>
        </div>
      </div>
    </div>
  )
}

