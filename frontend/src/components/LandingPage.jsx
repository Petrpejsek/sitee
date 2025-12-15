import { useState } from 'react'
import AuditForm from './AuditForm'
import { PRICING_PLANS, getYearlyPrice, getYearlySavings } from '../config/pricing'

// FAQ Accordion Item Component
function FAQItem({ question, answer }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="border-2 border-gray-200 rounded-xl overflow-hidden hover:border-blue-300 transition-colors">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-5 flex items-center justify-between bg-white hover:bg-gray-50 transition-colors text-left"
      >
        <span className="text-lg font-bold text-gray-900 pr-4">{question}</span>
        <svg
          className={`w-6 h-6 text-gray-600 flex-shrink-0 transition-transform duration-300 ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 py-5 bg-gray-50 border-t-2 border-gray-200">
          <div className="text-gray-700 leading-relaxed space-y-2">
            {answer}
          </div>
        </div>
      )}
    </div>
  )
}

export default function LandingPage({ onJobCreated }) {
  const [showForm, setShowForm] = useState(false)
  const [yearlyBilling, setYearlyBilling] = useState(false)
  const [heroInputValue, setHeroInputValue] = useState('')
  const [heroLoading, setHeroLoading] = useState(false)
  const [heroError, setHeroError] = useState(null)

  const scrollToForm = () => {
    setShowForm(true)
    setTimeout(() => {
      document.getElementById('audit-form')?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      })
    }, 100)
  }

  const scrollToFormWithDomain = (domain) => {
    setShowForm(true)
    setHeroInputValue(domain)
    setTimeout(() => {
      document.getElementById('audit-form')?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
      })
    }, 100)
  }

  // Helper: normalize domain
  const normalizeDomain = (input) => {
    return input
      .trim()
      .replace(/^https?:\/\//, '')  // Remove http(s)://
      .replace(/^www\./, '')         // Remove www.
      .replace(/\/.*$/, '')          // Remove path
      .toLowerCase()
  }

  // Start analysis directly from hero
  const handleHeroAnalyze = async () => {
    setHeroLoading(true)
    setHeroError(null)

    try {
      const normalizedDomain = normalizeDomain(heroInputValue)
      
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
      setHeroError(err.message)
      setHeroLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Sticky Navbar */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 backdrop-blur-lg bg-opacity-90">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-20 lg:h-24">
            {/* Logo */}
            <div className="flex items-center">
              <a href="/" className="cursor-pointer">
                <img 
                  src="/sitee-logo.png" 
                  alt="sitee.ai" 
                  className="h-24 lg:h-28 w-auto hover:opacity-80 transition-opacity"
                />
              </a>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              <a 
                href="#how-it-works" 
                className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                How It Works
              </a>
              <a 
                href="#faq" 
                className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                FAQ
              </a>
              <button
                onClick={scrollToForm}
                className="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-md hover:shadow-lg hover:scale-105 transition-all duration-200"
              >
                Start Free Audit
              </button>
            </div>

            {/* Mobile CTA */}
            <div className="md:hidden">
              <button
                onClick={scrollToForm}
                className="px-5 py-2 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-md"
              >
                Get Started
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-white">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-purple-50 opacity-70" />
        
        <div className="relative container mx-auto px-4 py-20 lg:py-32">
          <div className="max-w-5xl mx-auto text-center">
            {/* Main Headline */}
            <h1 className="text-5xl lg:text-7xl font-extrabold text-gray-900 mb-6 leading-tight">
              Is AI sending customers to
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
                your business?
              </span>
            </h1>

            {/* Single Explanation */}
            <p className="text-xl lg:text-2xl text-gray-600 mb-4 max-w-3xl mx-auto leading-relaxed">
              ChatGPT, Perplexity, and Gemini are already recommending companies.
            </p>

            {/* Single Emotional Line */}
            <p className="text-base lg:text-lg text-gray-700 mb-12 max-w-2xl mx-auto font-medium">
              See how to become one of them — without ads.
            </p>

            {/* Hero Inline Input */}
            <div className="mt-10 mb-12 max-w-2xl mx-auto">
              {heroError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm text-center">
                  {heroError}
                </div>
              )}
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  placeholder="yourwebsite.com"
                  value={heroInputValue}
                  onChange={(e) => setHeroInputValue(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && heroInputValue.trim() && !heroLoading) {
                      handleHeroAnalyze()
                    }
                  }}
                  disabled={heroLoading}
                  className="flex-1 px-5 py-4 text-lg border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <button
                  onClick={() => {
                    if (heroInputValue.trim() && !heroLoading) {
                      handleHeroAnalyze()
                    }
                  }}
                  disabled={heroLoading}
                  className="px-8 py-4 text-lg font-semibold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-200 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  {heroLoading ? 'Analyzing...' : 'Analyze Now'}
                </button>
              </div>
              <p className="mt-3 text-sm text-gray-500 text-center">
                Free • No credit card • Results in ~5 minutes
              </p>
            </div>

            {/* Checklist */}
            <div className="flex flex-wrap justify-center items-center gap-8 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>See if ChatGPT recommends you</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Understand why competitors win</span>
              </div>
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Get a clear AI action plan</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-20 bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
                Get Into AI Search Results — Fast & Affordable
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                ChatGPT, Perplexity, and Gemini are replacing Google for high-intent searches. If you're not visible there, you don't exist in AI search.
              </p>
            </div>

            {/* Stats Grid */}
            <div className="grid md:grid-cols-3 gap-8 mb-16">
              {/* Stat 1 */}
              <div className="bg-white rounded-2xl p-8 shadow-lg text-center transform hover:scale-105 transition-transform duration-300">
                <div className="text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 mb-4">
                  400%
                </div>
                <div className="text-lg font-bold text-gray-900 mb-2">
                  AI Search Growth
                </div>
                <p className="text-gray-600">
                  Annual growth rate of AI-powered search queries worldwide
                </p>
              </div>

              {/* Stat 2 */}
              <div className="bg-white rounded-2xl p-8 shadow-lg text-center transform hover:scale-105 transition-transform duration-300">
                <div className="text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600 mb-4">
                  2B+
                </div>
                <div className="text-lg font-bold text-gray-900 mb-2">
                  AI Queries Daily
                </div>
                <p className="text-gray-600">
                  People asking ChatGPT & Perplexity for recommendations every day
                </p>
              </div>

              {/* Stat 3 */}
              <div className="bg-white rounded-2xl p-8 shadow-lg text-center transform hover:scale-105 transition-transform duration-300">
                <div className="text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-pink-600 to-orange-600 mb-4">
                  10x
                </div>
                <div className="text-lg font-bold text-gray-900 mb-2">
                  More Leads Possible
                </div>
                <p className="text-gray-600">
                  Businesses optimized for AI get 10x more qualified traffic
                </p>
              </div>
            </div>

            {/* CTA Statement */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 lg:p-12 shadow-xl text-white">
              <div className="flex flex-col lg:flex-row items-center gap-8">
                <div className="flex-shrink-0">
                  <div className="w-20 h-20 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center shadow-lg">
                    <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1 text-center lg:text-left">
                  <h3 className="text-2xl lg:text-3xl font-bold mb-4">
                    We turn "AI ignores you" into "AI recommends you" — in 90 days.
                  </h3>
                  <p className="text-lg text-white/90 mb-4">
                    Start with a free audit. Get a concrete roadmap in minutes. Then we deliver the exact pages AI models need — month by month.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              We Know What AI Models Need to Recommend You
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              We analyze what AI models actually extract, cite, and recommend — then build it into your site step by step.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto mb-16">
            {/* Benefit 1 */}
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-blue-200">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <div className="text-4xl font-bold text-blue-600 mb-3">Month 1</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Visibility Foundation
              </h3>
              <p className="text-gray-700 leading-relaxed mb-4">
                We build the core pages AI models require to understand your business: clear About, Services, entity definitions, and proof signals. This is where AI finally "gets" what you do.
              </p>
              <p className="text-sm font-bold text-blue-700">
                Result: Your brand becomes visible to AI models.
              </p>
            </div>

            {/* Benefit 2 */}
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-purple-200">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <div className="text-4xl font-bold text-purple-600 mb-3">Month 2-3</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Recommendation Triggers
              </h3>
              <p className="text-gray-700 leading-relaxed mb-4">
                We add comparison pages, FAQs, and use-case content based on real AI prompts and extraction behavior. Visibility typically grows 3–5×.
              </p>
              <p className="text-sm font-bold text-purple-700">
                Result: AI models begin recommending you.
              </p>
            </div>

            {/* Benefit 3 */}
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-green-200">
              <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
              <div className="text-4xl font-bold text-green-600 mb-3">Month 4+</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Preferred Source
              </h3>
              <p className="text-gray-700 leading-relaxed mb-4">
                We continuously strengthen your authority with updates, stats, proof, and competitive positioning — so AI models prefer you over others.
              </p>
              <p className="text-sm font-bold text-green-700">
                Result: You become the preferred recommendation.
              </p>
            </div>
          </div>

          {/* Growth Stats */}
          <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 rounded-2xl p-12 shadow-2xl text-white max-w-5xl mx-auto">
            <div className="text-center mb-8">
              <h3 className="text-3xl font-bold mb-4">Average Client Growth</h3>
              <p className="text-xl text-white/90">Real results from businesses we've optimized for AI</p>
            </div>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="text-5xl font-extrabold mb-2">+245%</div>
                <div className="text-lg font-semibold">AI Traffic Growth</div>
                <div className="text-sm text-white/80 mt-1">in first 90 days</div>
              </div>
              <div className="text-center">
                <div className="text-5xl font-extrabold mb-2">8.5x</div>
                <div className="text-lg font-semibold">More AI Mentions</div>
                <div className="text-sm text-white/80 mt-1">across all models</div>
              </div>
              <div className="text-center">
                <div className="text-5xl font-extrabold mb-2">30%</div>
                <div className="text-lg font-semibold">Higher Conversion</div>
                <div className="text-sm text-white/80 mt-1">from AI visitors</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
              What You Get Every Month
            </h2>
            <p className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 mb-4">
              New pages added to your website — optimized to bring customers from AI for free
            </p>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              You have your website. We add new pages to it every month. These pages are written so ChatGPT, Perplexity, and other AI tools recommend YOUR business.
            </p>
          </div>

          <div className="max-w-6xl mx-auto">
            {/* Main Product Explanation Box */}
            <div className="bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 rounded-3xl p-8 lg:p-12 mb-12 border-2 border-blue-200 shadow-xl">
              <div className="grid md:grid-cols-2 gap-8 items-center">
                {/* Left: Simple explanation */}
                <div>
                  <div className="inline-block px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-full mb-6">
                    THIS IS WHAT WE DO
                  </div>
                  <h3 className="text-3xl font-bold text-gray-900 mb-6">
                    We Add Pages to Your Existing Website
                  </h3>
                  <div className="space-y-4 text-lg text-gray-700">
                    <p className="flex items-start gap-3">
                      <span className="text-2xl">✅</span>
                      <span><strong>You keep your website</strong> — we don't change anything</span>
                    </p>
                    <p className="flex items-start gap-3">
                      <span className="text-2xl">✅</span>
                      <span><strong>Every month we deliver new pages</strong> — ready to upload</span>
                    </p>
                    <p className="flex items-start gap-3">
                      <span className="text-2xl">✅</span>
                      <span><strong>We know exactly what ChatGPT needs to see</strong> — so we write pages that make AI recommend YOUR business</span>
                    </p>
                    <p className="flex items-start gap-3">
                      <span className="text-2xl">🚀</span>
                      <span><strong>More pages = more free traffic</strong> — it grows every month</span>
                    </p>
                  </div>
                </div>

                {/* Right: Visual example */}
                <div className="bg-white rounded-2xl p-6 shadow-xl border-2 border-purple-200">
                  <div className="text-center mb-5">
                    <div className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 mb-1">
                      YOUR GROWTH TRAJECTORY
                    </div>
                    <div className="text-xs font-semibold text-gray-500">Real results timeline</div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-orange-50 to-orange-100 rounded-xl border-l-4 border-orange-400">
                      <div className="text-base font-black text-orange-900 w-20">Month 1</div>
                      <div className="flex-1">
                        <div className="text-sm font-bold text-orange-900">AI Discovery Phase</div>
                        <div className="text-xs font-medium text-orange-700">AI starts understanding your business — first visitors arrive</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-lime-50 to-lime-100 rounded-xl border-l-4 border-lime-500">
                      <div className="text-base font-black text-lime-900 w-20">Month 3</div>
                      <div className="flex-1">
                        <div className="text-sm font-bold text-lime-900">Growing Customer Flow</div>
                        <div className="text-xs font-medium text-lime-800">Regular stream of high-intent customers from AI searches</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-green-50 to-green-100 rounded-xl border-l-4 border-green-500">
                      <div className="text-base font-black text-green-900 w-20">Month 6</div>
                      <div className="flex-1">
                        <div className="text-sm font-bold text-green-900">Strong Revenue Stream</div>
                        <div className="text-xs font-medium text-green-800">Lots of qualified customers weekly — zero ad spend</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-emerald-100 to-emerald-200 rounded-xl border-l-4 border-emerald-600 shadow-lg">
                      <div className="text-base font-black text-emerald-900 w-20">Month 12</div>
                      <div className="flex-1">
                        <div className="text-sm font-bold text-emerald-900">Massive Traffic Channel 🚀</div>
                        <div className="text-xs font-medium text-emerald-800">Huge volume of free customers, competitors still invisible to AI</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-5 p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-xl border-2 border-yellow-300 shadow-md">
                    <p className="text-sm font-black text-gray-900 text-center mb-1">
                      Each page = A Money Machine Working 24/7
                    </p>
                    <p className="text-xs font-bold text-yellow-900 text-center">
                      No ads. No cold calls. Just customers who already want what you offer.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* 3-Step Process */}
            <div className="grid md:grid-cols-3 gap-8 mb-12">
              {/* Step 1 */}
              <div className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center text-white text-2xl font-bold mb-6 shadow-lg">
                    1
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">
                    We Find What's Missing
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    We identify exactly which pages your website needs so AI tools like ChatGPT and Perplexity start recommending your business to customers.
                  </p>
                </div>
                {/* Arrow */}
                <div className="hidden md:block absolute top-8 -right-4 text-gray-300">
                  <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Step 2 */}
              <div className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center text-white text-2xl font-bold mb-6 shadow-lg">
                    2
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">
                    New Pages Every Month
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    Every month we deliver new complete pages, ready to publish on your website. No work needed from you — just add them and they start working.
                  </p>
                </div>
                {/* Arrow */}
                <div className="hidden md:block absolute top-8 -right-4 text-gray-300">
                  <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-pink-500 to-red-500 rounded-2xl flex items-center justify-center text-white text-2xl font-bold mb-6 shadow-lg">
                  3
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">
                  Pages Work 24/7 for You
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  The pages stay on your website permanently and bring customers long-term — without ads, without ongoing marketing spend.
                </p>
              </div>
            </div>

            {/* Bottom emphasis */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 lg:p-10 shadow-2xl text-white text-center">
              <h3 className="text-3xl lg:text-4xl font-bold mb-4">
                It's Really This Simple
              </h3>
              <p className="text-xl lg:text-2xl mb-4 max-w-3xl mx-auto leading-relaxed">
                You have a website. We add pages to it every month. Those pages bring customers without ads. The longer you continue, the more traffic you build.
              </p>
              <p className="text-lg mb-6 max-w-2xl mx-auto font-semibold text-white/90">
                These pages stay on your website permanently — even if you stop later.
              </p>
              <div className="inline-flex items-center gap-3 px-6 py-3 bg-white/20 backdrop-blur-sm rounded-xl">
                <span className="text-2xl">💡</span>
                <span className="text-lg font-bold">Most people don't even know ChatGPT can recommend businesses</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
                Frequently Asked Questions
              </h2>
            </div>

            {/* FAQ Categories */}
            <div className="space-y-12">
              {/* PRODUCT & SAFETY */}
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-blue-500">
                  Product & Safety
                </h3>
                <div className="space-y-4">
                  <FAQItem
                    question="Do you change my existing website?"
                    answer={<>
                      <p className="mb-2">No. Your website stays exactly the same.</p>
                      <p>We only add new pages alongside it — nothing is removed or modified.</p>
                    </>}
                  />
                  <FAQItem
                    question="Can this hurt my SEO or Google rankings?"
                    answer={<>
                      <p className="mb-2">No. These pages help search engines and AI tools understand your business better.</p>
                      <p>They are designed to be safe, helpful, and long-term.</p>
                    </>}
                  />
                  <FAQItem
                    question="Is this risky or experimental?"
                    answer={<>
                      <p className="mb-2">No. AI tools already recommend companies today.</p>
                      <p>We simply create the type of content they already rely on.</p>
                    </>}
                  />
                </div>
              </div>

              {/* WHAT YOU ACTUALLY GET */}
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-purple-500">
                  What You Actually Get
                </h3>
                <div className="space-y-4">
                  <FAQItem
                    question="What exactly do I get every month?"
                    answer={<>
                      <p className="mb-2">You receive new, ready-to-publish pages written specifically for your business.</p>
                      <p>Each page targets real questions potential customers ask.</p>
                    </>}
                  />
                  <FAQItem
                    question="Are these blog posts?"
                    answer={<>
                      <p className="mb-2">No. These are customer-acquisition pages.</p>
                      <p>They are designed to bring demand, not just traffic.</p>
                    </>}
                  />
                  <FAQItem
                    question="Do I need to do any work?"
                    answer={<>
                      <p className="mb-2">No. We do everything for you.</p>
                      <p>You only upload the pages to your website.</p>
                    </>}
                  />
                </div>
              </div>

              {/* RESULTS & TIMING */}
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-green-500">
                  Results & Timing
                </h3>
                <div className="space-y-4">
                  <FAQItem
                    question="When will I start seeing results?"
                    answer={<>
                      <p className="mb-2">Most clients see early visibility within the first 1–3 months.</p>
                      <p>Results grow as more pages are added over time.</p>
                    </>}
                  />
                  <FAQItem
                    question="Why does this work better over time?"
                    answer={<>
                      <p className="mb-2">Because each page stays on your website permanently.</p>
                      <p>More pages mean more opportunities to get recommended.</p>
                    </>}
                  />
                  <FAQItem
                    question="Is the traffic really free?"
                    answer={<>
                      <p>Yes. There are no ads, no clicks to pay for, and no ongoing marketing spend.</p>
                    </>}
                  />
                </div>
              </div>

              {/* PRICING & COMMITMENT */}
              <div>
                <h3 className="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-orange-500">
                  Pricing & Commitment
                </h3>
                <div className="space-y-4">
                  <FAQItem
                    question="Is there a long-term contract?"
                    answer={<>
                      <p>No. You can cancel anytime.</p>
                    </>}
                  />
                  <FAQItem
                    question="What happens if I stop after a few months?"
                    answer={<>
                      <p className="mb-2">All pages stay on your website permanently.</p>
                      <p>You keep everything we created.</p>
                    </>}
                  />
                  <FAQItem
                    question="Why is this a monthly service?"
                    answer={<>
                      <p className="mb-2">AI tools reward websites that grow and expand over time.</p>
                      <p>Adding pages monthly builds stronger and more consistent visibility.</p>
                    </>}
                  />
                </div>
              </div>
            </div>

            {/* Final Note */}
            <div className="mt-16 p-8 bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl border-2 border-blue-200 text-center">
              <p className="text-lg font-bold text-gray-900">
                These pages stay on your website permanently — even if you stop later.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              Your Monthly AI Growth Package
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Every month, we deliver ready-to-use pages optimized for AI models. No guesswork, just plug and grow.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
            {/* Feature 1 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Ready-Made Pages
              </h3>
              <p className="text-gray-600 leading-relaxed">
                We create optimized About, Services, Case Studies, and FAQ pages that AI models love to reference
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                AI-Friendly Content
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Structured data, clear comparisons, and proof points formatted exactly how ChatGPT and Perplexity extract info
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-pink-500 to-pink-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Monthly Updates
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Fresh content every month keeps AI models seeing you as active and authoritative in your space
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Competitor Tracking
              </h3>
              <p className="text-gray-600 leading-relaxed">
                We monitor what's working for your competitors and make sure you stay ahead in AI recommendations
              </p>
            </div>

            {/* Feature 5 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Growth Analytics
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Track your AI visibility score month-over-month and see exactly which pages are getting recommended
              </p>
            </div>

            {/* Feature 6 */}
            <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl flex items-center justify-center mb-6 shadow-md">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                Plug & Play Setup
              </h3>
              <p className="text-gray-600 leading-relaxed">
                No technical work needed. We deliver pages, you publish them. Simple integration with any CMS or website
              </p>
            </div>
          </div>

          {/* CTA Box */}
          <div className="mt-16 max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl p-10 shadow-xl border-2 border-blue-200">
              <div className="text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 mb-6 text-sm font-bold text-blue-700 bg-blue-100 rounded-full">
                  ✅ Start with a Free Audit
                </div>
                <h3 className="text-3xl font-bold text-gray-900 mb-4">
                  See Why AI Doesn't Recommend Your Site (Yet)
                </h3>
                <p className="text-lg text-gray-600 mb-6">
                  Get your free AI visibility audit first. We show you exactly which pages, data, and signals AI models expect — then deliver those pages ready-made every month.
                </p>
                <button
                  onClick={() => document.getElementById('audit-form')?.scrollIntoView({ behavior: 'smooth' })}
                  className="px-10 py-4 text-lg font-bold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-200"
                >
                  Start My Free AI Visibility Audit
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-3 gap-12 text-center">
              <div>
                <div className="text-5xl lg:text-6xl font-extrabold mb-3">60+</div>
                <div className="text-xl opacity-90">Pages Analyzed Per Domain</div>
              </div>
              <div>
                <div className="text-5xl lg:text-6xl font-extrabold mb-3">5-10min</div>
                <div className="text-xl opacity-90">Complete Analysis Time</div>
              </div>
              <div>
                <div className="text-5xl lg:text-6xl font-extrabold mb-3">100%</div>
                <div className="text-xl opacity-90">Actionable Insights</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* What's in Your Audit Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              What's In Your Free AI Visibility Audit
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              You'll see exactly how AI systems understand your business today — and why they do or don't recommend you.
            </p>
          </div>

          {/* Free audit content */}
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                ),
                title: "AI Visibility Score",
                description: "How visible your business is across ChatGPT, Gemini, and Perplexity right now."
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                ),
                title: "Recommendation Gaps",
                description: "Concrete reasons why AI systems skip your company and recommend competitors instead."
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                ),
                title: "Missing Signals & Pages",
                description: "Which pages, entities, and data points AI models expect — but don't find on your site."
              }
            ].map((feature, index) => (
              <div key={index} className="bg-emerald-50 rounded-xl p-6 border border-emerald-200">
                <div className="w-12 h-12 bg-emerald-600 rounded-lg flex items-center justify-center text-white mb-4">
                  {feature.icon}
                </div>
                <h4 className="text-lg font-bold text-gray-900 mb-2">
                  {feature.title}
                </h4>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-6 mb-16">
            <div className="mb-3 text-sm font-black uppercase tracking-wider text-gray-600">
              Choose your AI visibility growth
            </div>
            <h2 className="text-3xl lg:text-4xl font-black text-gray-900">
              How fast do you want to grow in AI channels?
            </h2>
            
            {/* MONTHLY/YEARLY TOGGLE */}
            <div className="flex items-center justify-center gap-4">
              <span className={`text-base font-bold ${!yearlyBilling ? 'text-gray-900' : 'text-gray-500'}`}>
                Monthly
              </span>
              <button
                onClick={() => setYearlyBilling(!yearlyBilling)}
                className={`relative inline-flex h-8 w-16 items-center rounded-full transition-colors ${
                  yearlyBilling ? 'bg-emerald-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    yearlyBilling ? 'translate-x-9' : 'translate-x-1'
                  }`}
                />
              </button>
              <div className="flex items-center gap-2">
                <span className={`text-base font-bold ${yearlyBilling ? 'text-gray-900' : 'text-gray-500'}`}>
                  Yearly
                </span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-700">
                  Save 25%
                </span>
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3 max-w-7xl mx-auto">
            
            {/* STARTER */}
            <div className="flex flex-col rounded-2xl border-2 border-gray-300 bg-white p-8 shadow-md hover:shadow-xl transition-all">
              <div className="mb-4">
                <div className="text-2xl font-black text-gray-900">{PRICING_PLANS.starter.label}</div>
                <div className="mt-1 text-sm font-semibold text-gray-600">{PRICING_PLANS.starter.tagline}</div>
              </div>
              
              <div className="mb-6 rounded-lg border-2 border-gray-200 bg-gray-50 p-4">
                <div className="flex items-center gap-2">
                  <span className="text-5xl font-black text-gray-900">{PRICING_PLANS.starter.pagesPerMonth}</span>
                  <div className="text-sm font-bold text-gray-600">
                    <div>AI-ready pages</div>
                    <div>every month</div>
                  </div>
                </div>
                <div className="mt-3 rounded-md bg-blue-100 px-3 py-2">
                  <div className="text-xs font-bold text-blue-900">Expected annual growth:</div>
                  <div className="text-2xl font-black text-blue-900">{PRICING_PLANS.starter.expectedGrowth}</div>
                  <div className="text-xs font-semibold text-blue-700">{PRICING_PLANS.starter.expectedGrowthLabel}</div>
                </div>
              </div>

              <div className="mb-4 text-center">
                {yearlyBilling ? (
                  <>
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <span className="text-lg font-bold text-gray-400 line-through">${PRICING_PLANS.starter.monthlyPrice}</span>
                      <span className="rounded-md bg-emerald-600 px-3 py-1 text-sm font-black text-white">
                        25% OFF
                      </span>
                    </div>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-sm font-bold text-gray-500">$</span>
                      <span className="text-5xl font-black text-gray-900">{getYearlyPrice(PRICING_PLANS.starter.monthlyPrice)}</span>
                      <span className="text-lg font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-1">USD per month, billed annually</div>
                    <div className="mt-2 text-sm font-bold text-emerald-600">
                      Save ${getYearlySavings(PRICING_PLANS.starter.monthlyPrice).toLocaleString()}/year
                    </div>
                    <div className="mt-2 px-3 py-1 bg-blue-100 rounded-full text-xs font-bold text-blue-800">
                      + Full AI Audit included ($199 value)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-sm font-bold text-gray-500">$</span>
                      <span className="text-5xl font-black text-gray-900">{PRICING_PLANS.starter.monthlyPrice}</span>
                      <span className="text-lg font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-1">USD per month</div>
                  </>
                )}
              </div>

              <div className="mb-6 flex-1 space-y-3 text-sm font-medium text-gray-700">
                {PRICING_PLANS.starter.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-600">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button 
                onClick={() => document.getElementById('audit-form')?.scrollIntoView({ behavior: 'smooth' })}
                className="w-full rounded-xl border-2 border-gray-300 bg-white py-4 text-base font-bold text-gray-900 hover:bg-gray-50 transition-all"
              >
                {PRICING_PLANS.starter.ctaLabel}
              </button>
            </div>

            {/* GROWTH */}
            <div className="relative flex flex-col rounded-2xl border-2 border-emerald-600 bg-white p-8 shadow-xl hover:shadow-2xl transition-all scale-105">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <div className="rounded-full bg-emerald-600 px-5 py-1.5 text-xs font-black uppercase tracking-wider text-white shadow-lg">
                  Most Popular
                </div>
              </div>

              <div className="mb-4">
                <div className="text-2xl font-black text-gray-900">{PRICING_PLANS.growth.label}</div>
                <div className="mt-1 text-sm font-semibold text-emerald-700">{PRICING_PLANS.growth.tagline}</div>
              </div>
              
              <div className="mb-6 rounded-lg border-2 border-emerald-500 bg-emerald-50 p-4">
                <div className="flex items-center gap-2">
                  <span className="text-5xl font-black text-emerald-900">{PRICING_PLANS.growth.pagesPerMonth}</span>
                  <div className="text-sm font-bold text-emerald-800">
                    <div>AI-ready pages</div>
                    <div>every month</div>
                  </div>
                </div>
                <div className="mt-3 rounded-md bg-emerald-600 px-3 py-2">
                  <div className="text-xs font-bold text-emerald-100">Expected annual growth:</div>
                  <div className="text-2xl font-black text-white">{PRICING_PLANS.growth.expectedGrowth}</div>
                  <div className="text-xs font-semibold text-emerald-100">{PRICING_PLANS.growth.expectedGrowthLabel}</div>
                </div>
              </div>

              <div className="mb-4 text-center">
                {yearlyBilling ? (
                  <>
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <span className="text-lg font-bold text-gray-400 line-through">${PRICING_PLANS.growth.monthlyPrice}</span>
                      <span className="rounded-md bg-emerald-600 px-3 py-1 text-sm font-black text-white">
                        25% OFF
                      </span>
                    </div>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-sm font-bold text-gray-500">$</span>
                      <span className="text-5xl font-black text-gray-900">{getYearlyPrice(PRICING_PLANS.growth.monthlyPrice)}</span>
                      <span className="text-lg font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-1">USD per month, billed annually</div>
                    <div className="mt-2 text-sm font-bold text-emerald-600">
                      Save ${getYearlySavings(PRICING_PLANS.growth.monthlyPrice).toLocaleString()}/year
                    </div>
                    <div className="mt-2 px-3 py-1 bg-blue-100 rounded-full text-xs font-bold text-blue-800">
                      + Full AI Audit included ($199 value)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-sm font-bold text-gray-500">$</span>
                      <span className="text-5xl font-black text-gray-900">{PRICING_PLANS.growth.monthlyPrice}</span>
                      <span className="text-lg font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-1">USD per month</div>
                  </>
                )}
              </div>

              <div className="mb-6 flex-1 space-y-3 text-sm font-semibold text-gray-800">
                {PRICING_PLANS.growth.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-600">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button 
                onClick={() => document.getElementById('audit-form')?.scrollIntoView({ behavior: 'smooth' })}
                className="w-full rounded-xl bg-emerald-600 py-4 text-base font-bold text-white hover:bg-emerald-700 transition-all shadow-lg"
              >
                {PRICING_PLANS.growth.ctaLabel}
              </button>
            </div>

            {/* SCALE */}
            <div className="flex flex-col rounded-2xl border-2 border-gray-300 bg-white p-8 shadow-md hover:shadow-xl transition-all">
              <div className="mb-4">
                <div className="text-2xl font-black text-gray-900">{PRICING_PLANS.scale.label}</div>
                <div className="mt-1 text-sm font-semibold text-gray-600">{PRICING_PLANS.scale.tagline}</div>
              </div>
              
              <div className="mb-6 rounded-lg border-2 border-gray-200 bg-gray-50 p-4">
                <div className="flex items-center gap-2">
                  <span className="text-5xl font-black text-gray-900">{PRICING_PLANS.scale.pagesPerMonth}</span>
                  <div className="text-sm font-bold text-gray-600">
                    <div>AI-ready pages</div>
                    <div>every month</div>
                  </div>
                </div>
                <div className="mt-3 rounded-md bg-gradient-to-r from-orange-400 to-red-500 px-3 py-2">
                  <div className="text-xs font-bold text-white">Expected annual growth:</div>
                  <div className="text-2xl font-black text-white">{PRICING_PLANS.scale.expectedGrowth}</div>
                  <div className="text-xs font-semibold text-orange-100">{PRICING_PLANS.scale.expectedGrowthLabel}</div>
                </div>
              </div>

              <div className="mb-4 text-center">
                {yearlyBilling ? (
                  <>
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <span className="text-lg font-bold text-gray-400 line-through">${PRICING_PLANS.scale.monthlyPrice}</span>
                      <span className="rounded-md bg-emerald-600 px-3 py-1 text-sm font-black text-white">
                        25% OFF
                      </span>
                    </div>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-sm font-bold text-gray-500">$</span>
                      <span className="text-5xl font-black text-gray-900">{getYearlyPrice(PRICING_PLANS.scale.monthlyPrice)}</span>
                      <span className="text-lg font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-1">USD per month, billed annually</div>
                    <div className="mt-2 text-sm font-bold text-emerald-600">
                      Save ${getYearlySavings(PRICING_PLANS.scale.monthlyPrice).toLocaleString()}/year
                    </div>
                    <div className="mt-2 px-3 py-1 bg-blue-100 rounded-full text-xs font-bold text-blue-800">
                      + Full AI Audit included ($199 value)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-sm font-bold text-gray-500">$</span>
                      <span className="text-5xl font-black text-gray-900">{PRICING_PLANS.scale.monthlyPrice}</span>
                      <span className="text-lg font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-1">USD per month</div>
                  </>
                )}
              </div>

              <div className="mb-6 flex-1 space-y-3 text-sm font-medium text-gray-700">
                {PRICING_PLANS.scale.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-600">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button 
                onClick={() => document.getElementById('audit-form')?.scrollIntoView({ behavior: 'smooth' })}
                className="w-full rounded-xl border-2 border-gray-300 bg-white py-4 text-base font-bold text-gray-900 hover:bg-gray-50 transition-all"
              >
                {PRICING_PLANS.scale.ctaLabel}
              </button>
            </div>
          </div>

          {/* BOTTOM VALUE STATEMENT */}
          <div className="mt-12 rounded-xl border-2 border-emerald-500 bg-gradient-to-r from-emerald-50 to-white p-8 text-center shadow-lg max-w-5xl mx-auto">
            <div className="text-2xl font-black text-gray-900 mb-2">
              Your AI visibility grows every month you stay subscribed
            </div>
            <div className="text-base font-semibold text-gray-700 mb-4">
              More AI-ready pages = more recommendations across ChatGPT, Claude, Gemini, Perplexity, Copilot & all major AI platforms
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-600 px-6 py-3 text-sm font-bold text-white">
              <span className="text-lg">🚀</span>
              <span>This is a completely new channel — your competitors aren't there yet</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Form Section */}
      <section id="audit-form" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center mb-12">
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              Ready to Boost Your AI Visibility?
            </h2>
            <p className="text-xl text-gray-600">
              Get your free comprehensive audit in just 5 minutes. No credit card required.
            </p>
          </div>

          {showForm ? (
            <AuditForm onJobCreated={onJobCreated} initialDomain={heroInputValue} />
          ) : (
            <div className="max-w-2xl mx-auto text-center">
              <button
                onClick={() => setShowForm(true)}
                className="px-12 py-5 text-xl font-bold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-2xl hover:shadow-3xl hover:scale-105 transition-all duration-300"
              >
                Start Your Free AI Audit
              </button>
              
              {/* Audit explainer - what you get */}
              <div className="mt-8 p-6 bg-gray-50 rounded-xl border border-gray-200 text-left">
                <div className="text-sm font-bold text-gray-900 mb-3">Your free audit includes:</div>
                <ul className="space-y-2 text-sm text-gray-700">
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-600 mt-0.5">✓</span>
                    <span><strong>AI Visibility Score</strong> — how AI systems currently see your business</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-emerald-600 mt-0.5">✓</span>
                    <span><strong>Top Problems</strong> — critical gaps blocking AI recommendations</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600 mt-0.5">💡</span>
                    <span><strong>Action Plan (Section 6)</strong> — detailed roadmap available with full audit</span>
                  </li>
                </ul>
                <div className="mt-4 pt-3 border-t border-gray-200 text-xs text-gray-500">
                  No credit card required. Audit = diagnosis. Subscription = solution.
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid md:grid-cols-3 gap-8 mb-8">
              <div>
                <div className="mb-4">
                  <img 
                    src="/sitee-logo.png" 
                    alt="sitee.ai" 
                    className="h-20 w-auto brightness-0 invert"
                  />
                </div>
                <p className="text-sm leading-relaxed">
                  The first comprehensive platform for analyzing and optimizing 
                  your AI visibility across ChatGPT, Gemini, and Perplexity.
                </p>
              </div>
              <div>
                <h4 className="text-white text-lg font-bold mb-4">Product</h4>
                <ul className="space-y-2 text-sm">
                  <li><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></li>
                  <li><a href="#audit-form" className="hover:text-white transition-colors">Get Started</a></li>
                  <li><a href="#" className="hover:text-white transition-colors">Features</a></li>
                </ul>
              </div>
              <div>
                <h4 className="text-white text-lg font-bold mb-4">About</h4>
                <ul className="space-y-2 text-sm">
                  <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                  <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                  <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
                </ul>
              </div>
            </div>
            <div className="border-t border-gray-800 pt-8 text-center text-sm">
              <p>&copy; {new Date().getFullYear()} LLM Audit Engine. All rights reserved.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
