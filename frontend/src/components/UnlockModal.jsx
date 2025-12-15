import { useState } from 'react'
import { PRICING_PLANS, AUDIT_UNLOCK_PRICE, getYearlyPrice, getYearlySavings } from '../config/pricing'

export default function UnlockModal({ auditId, onClose }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedPlan, setSelectedPlan] = useState('growth')
  const [yearlyBilling, setYearlyBilling] = useState(false)

  const handleUnlockAudit = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/payments/create-audit-checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          audit_id: auditId
        })
      })

      if (!response.ok) {
        throw new Error('Failed to create checkout session')
      }

      const data = await response.json()
      // Redirect to Stripe checkout
      window.location.href = data.url
    } catch (err) {
      setError('Failed to start payment. Please try again.')
      setLoading(false)
    }
  }

  const handleSubscribe = async (plan) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/payments/create-subscription-checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          plan: plan,
          audit_id: auditId
        })
      })

      if (!response.ok) {
        throw new Error('Failed to create checkout session')
      }

      const data = await response.json()
      // Redirect to Stripe checkout
      window.location.href = data.url
    } catch (err) {
      setError('Failed to start subscription. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl border border-gray-200 bg-white shadow-2xl">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div className="p-8">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Turn AI into your traffic channel</h2>
            <p className="text-lg text-gray-700 font-medium">Get recommended by ChatGPT, Gemini & Perplexity — without ads</p>
          </div>

          {error && (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
              {error}
            </div>
          )}

          {/* One-time payment option - with clear FREE message */}
          <div className="mb-8 px-6 py-5 rounded-xl border-2 border-blue-300 bg-gradient-to-r from-blue-50 to-purple-50 shadow-lg">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-3xl font-black text-gray-900">${AUDIT_UNLOCK_PRICE}</span>
                  <span className="text-sm text-gray-500 font-semibold">one-time payment</span>
                </div>
                <p className="text-sm text-gray-700 font-medium mb-2">
                  Full audit (Sections 1-6) • Action Plan included
                </p>
                <div className="inline-block px-4 py-2 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg shadow-md">
                  <p className="text-base text-white font-black flex items-center gap-2">
                    <span className="text-xl">🎁</span>
                    FREE with Growth or Scale subscription
                  </p>
                </div>
              </div>
              <button
                onClick={handleUnlockAudit}
                disabled={loading}
                className="rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 border-2 border-transparent px-6 py-3 text-base font-bold text-white transition-all hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 whitespace-nowrap shadow-lg hover:shadow-xl hover:scale-105"
              >
                {loading ? 'Processing...' : 'Get Full Audit'}
              </button>
            </div>
          </div>

          {/* Subscription options - PRIMARY */}
          <div className="mb-4">
            <div className="text-center mb-1">
              <h3 className="text-xl font-bold text-gray-900 mb-1">
                Build Continuous AI Visibility
              </h3>
              <p className="text-sm text-gray-600 font-medium">
                Ongoing optimization • Full audit included FREE • Cancel anytime
              </p>
            </div>
            
            {/* Monthly/Yearly Toggle */}
            <div className="flex items-center justify-center gap-2.5 mb-4 mt-3">
              <span className={`text-xs font-bold ${!yearlyBilling ? 'text-gray-900' : 'text-gray-500'}`}>
                Monthly
              </span>
              <button
                onClick={() => setYearlyBilling(!yearlyBilling)}
                className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors ${
                  yearlyBilling ? 'bg-emerald-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    yearlyBilling ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <div className="flex items-center gap-1.5">
                <span className={`text-xs font-bold ${yearlyBilling ? 'text-gray-900' : 'text-gray-500'}`}>
                  Yearly
                </span>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-black text-emerald-700">
                  -25%
                </span>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            
            {/* STARTER */}
            <div className="flex flex-col rounded-xl border-2 border-gray-300 bg-white p-5 shadow-sm hover:shadow-md transition-all">
              <div className="mb-3">
                <div className="text-lg font-black text-gray-900">{PRICING_PLANS.starter.label}</div>
                <div className="mt-0.5 text-xs font-semibold text-gray-600">{PRICING_PLANS.starter.tagline}</div>
              </div>
              
              <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="flex items-center gap-2">
                  <span className="text-4xl font-black text-gray-900">{PRICING_PLANS.starter.pagesPerMonth}</span>
                  <div className="text-xs font-bold text-gray-600">
                    <div>AI-ready pages</div>
                    <div>every month</div>
                  </div>
                </div>
                <div className="mt-2 rounded-md bg-blue-100 px-2 py-1.5">
                  <div className="text-xs font-bold text-blue-900">Expected annual growth:</div>
                  <div className="text-xl font-black text-blue-900">{PRICING_PLANS.starter.expectedGrowth}</div>
                  <div className="text-xs font-semibold text-blue-700">{PRICING_PLANS.starter.expectedGrowthLabel}</div>
                </div>
              </div>

              <div className="mb-3 text-center">
                {yearlyBilling ? (
                  <>
                    <div className="flex items-center justify-center gap-1.5 mb-1">
                      <span className="text-sm font-bold text-gray-400 line-through">${PRICING_PLANS.starter.monthlyPrice}</span>
                      <span className="rounded-md bg-emerald-600 px-2 py-0.5 text-xs font-black text-white">
                        25% OFF
                      </span>
                    </div>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-xs font-bold text-gray-500">$</span>
                      <span className="text-4xl font-black text-gray-900">{getYearlyPrice(PRICING_PLANS.starter.monthlyPrice)}</span>
                      <span className="text-sm font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-0.5">USD per month, billed annually</div>
                    <div className="mt-1 text-xs font-bold text-emerald-600">
                      Save ${getYearlySavings(PRICING_PLANS.starter.monthlyPrice).toLocaleString()}/year
                    </div>
                    <div className="mt-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg text-xs font-black text-white shadow-md">
                      🎁 Full AI Audit FREE (${AUDIT_UNLOCK_PRICE} value)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-xs font-bold text-gray-500">$</span>
                      <span className="text-4xl font-black text-gray-900">{PRICING_PLANS.starter.monthlyPrice}</span>
                      <span className="text-sm font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-0.5">USD per month</div>
                  </>
                )}
              </div>

              <div className="mb-4 flex-1 space-y-2 text-xs font-medium text-gray-700">
                {PRICING_PLANS.starter.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <span className="text-emerald-600">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={() => handleSubscribe('starter')}
                disabled={loading}
                className="w-full rounded-lg border-2 border-gray-300 bg-white py-2.5 text-sm font-bold text-gray-900 hover:bg-gray-50 transition-all disabled:opacity-50"
              >
                {loading ? 'Processing...' : PRICING_PLANS.starter.ctaLabel}
              </button>
            </div>

            {/* GROWTH */}
            <div className="relative flex flex-col rounded-xl border-2 border-emerald-600 bg-white p-5 shadow-lg hover:shadow-xl transition-all">
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2">
                <div className="rounded-full bg-emerald-600 px-4 py-1 text-xs font-black uppercase tracking-wider text-white shadow-md">
                  Most Popular
                </div>
              </div>

              <div className="mb-3">
                <div className="text-lg font-black text-gray-900">{PRICING_PLANS.growth.label}</div>
                <div className="mt-0.5 text-xs font-semibold text-emerald-700">{PRICING_PLANS.growth.tagline}</div>
              </div>
              
              <div className="mb-4 rounded-lg border border-emerald-500 bg-emerald-50 p-3">
                <div className="flex items-center gap-2">
                  <span className="text-4xl font-black text-emerald-900">{PRICING_PLANS.growth.pagesPerMonth}</span>
                  <div className="text-xs font-bold text-emerald-800">
                    <div>AI-ready pages</div>
                    <div>every month</div>
                  </div>
                </div>
                <div className="mt-2 rounded-md bg-emerald-600 px-2 py-1.5">
                  <div className="text-xs font-bold text-emerald-100">Expected annual growth:</div>
                  <div className="text-xl font-black text-white">{PRICING_PLANS.growth.expectedGrowth}</div>
                  <div className="text-xs font-semibold text-emerald-100">{PRICING_PLANS.growth.expectedGrowthLabel}</div>
                </div>
              </div>

              <div className="mb-3 text-center">
                {yearlyBilling ? (
                  <>
                    <div className="flex items-center justify-center gap-1.5 mb-1">
                      <span className="text-sm font-bold text-gray-400 line-through">${PRICING_PLANS.growth.monthlyPrice}</span>
                      <span className="rounded-md bg-emerald-600 px-2 py-0.5 text-xs font-black text-white">
                        25% OFF
                      </span>
                    </div>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-xs font-bold text-gray-500">$</span>
                      <span className="text-4xl font-black text-gray-900">{getYearlyPrice(PRICING_PLANS.growth.monthlyPrice)}</span>
                      <span className="text-sm font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-0.5">USD per month, billed annually</div>
                    <div className="mt-1 text-xs font-bold text-emerald-600">
                      Save ${getYearlySavings(PRICING_PLANS.growth.monthlyPrice).toLocaleString()}/year
                    </div>
                    <div className="mt-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg text-xs font-black text-white shadow-md">
                      🎁 Full AI Audit FREE (${AUDIT_UNLOCK_PRICE} value)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-xs font-bold text-gray-500">$</span>
                      <span className="text-4xl font-black text-gray-900">{PRICING_PLANS.growth.monthlyPrice}</span>
                      <span className="text-sm font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-0.5">USD per month</div>
                    <div className="mt-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg text-xs font-black text-white shadow-md">
                      🎁 Full AI Audit FREE (${AUDIT_UNLOCK_PRICE} value)
                    </div>
                  </>
                )}
              </div>

              <div className="mb-4 flex-1 space-y-2 text-xs font-semibold text-gray-800">
                {PRICING_PLANS.growth.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <span className="text-emerald-600">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={() => handleSubscribe('growth')}
                disabled={loading}
                className="w-full rounded-lg bg-emerald-600 py-2.5 text-sm font-bold text-white hover:bg-emerald-700 transition-all shadow-md disabled:opacity-50"
              >
                {loading ? 'Processing...' : PRICING_PLANS.growth.ctaLabel}
              </button>
            </div>

            {/* SCALE */}
            <div className="flex flex-col rounded-xl border-2 border-gray-300 bg-white p-5 shadow-sm hover:shadow-md transition-all">
              <div className="mb-3">
                <div className="text-lg font-black text-gray-900">{PRICING_PLANS.scale.label}</div>
                <div className="mt-0.5 text-xs font-semibold text-gray-600">{PRICING_PLANS.scale.tagline}</div>
              </div>
              
              <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="flex items-center gap-2">
                  <span className="text-4xl font-black text-gray-900">{PRICING_PLANS.scale.pagesPerMonth}</span>
                  <div className="text-xs font-bold text-gray-600">
                    <div>AI-ready pages</div>
                    <div>every month</div>
                  </div>
                </div>
                <div className="mt-2 rounded-md bg-gradient-to-r from-orange-400 to-red-500 px-2 py-1.5">
                  <div className="text-xs font-bold text-white">Expected annual growth:</div>
                  <div className="text-xl font-black text-white">{PRICING_PLANS.scale.expectedGrowth}</div>
                  <div className="text-xs font-semibold text-orange-100">{PRICING_PLANS.scale.expectedGrowthLabel}</div>
                </div>
              </div>

              <div className="mb-3 text-center">
                {yearlyBilling ? (
                  <>
                    <div className="flex items-center justify-center gap-1.5 mb-1">
                      <span className="text-sm font-bold text-gray-400 line-through">${PRICING_PLANS.scale.monthlyPrice}</span>
                      <span className="rounded-md bg-emerald-600 px-2 py-0.5 text-xs font-black text-white">
                        25% OFF
                      </span>
                    </div>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-xs font-bold text-gray-500">$</span>
                      <span className="text-4xl font-black text-gray-900">{getYearlyPrice(PRICING_PLANS.scale.monthlyPrice)}</span>
                      <span className="text-sm font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-0.5">USD per month, billed annually</div>
                    <div className="mt-1 text-xs font-bold text-emerald-600">
                      Save ${getYearlySavings(PRICING_PLANS.scale.monthlyPrice).toLocaleString()}/year
                    </div>
                    <div className="mt-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg text-xs font-black text-white shadow-md">
                      🎁 Full AI Audit FREE (${AUDIT_UNLOCK_PRICE} value)
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-xs font-bold text-gray-500">$</span>
                      <span className="text-4xl font-black text-gray-900">{PRICING_PLANS.scale.monthlyPrice}</span>
                      <span className="text-sm font-bold text-gray-500">/mo</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-500 mt-0.5">USD per month</div>
                    <div className="mt-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-green-600 rounded-lg text-xs font-black text-white shadow-md">
                      🎁 Full AI Audit FREE (${AUDIT_UNLOCK_PRICE} value)
                    </div>
                  </>
                )}
              </div>

              <div className="mb-4 flex-1 space-y-2 text-xs font-medium text-gray-700">
                {PRICING_PLANS.scale.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <span className="text-emerald-600">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={() => handleSubscribe('scale')}
                disabled={loading}
                className="w-full rounded-lg border-2 border-gray-300 bg-white py-2.5 text-sm font-bold text-gray-900 hover:bg-gray-50 transition-all disabled:opacity-50"
              >
                {loading ? 'Processing...' : PRICING_PLANS.scale.ctaLabel}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
