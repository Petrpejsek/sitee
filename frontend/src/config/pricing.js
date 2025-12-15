/**
 * SINGLE SOURCE OF TRUTH FOR PRICING
 * 
 * All pricing cards, modals, paywall, and checkout must use this config.
 * DO NOT hardcode prices elsewhere.
 */

export const PRICING_PLANS = {
  starter: {
    id: 'starter',
    label: 'Starter',
    tagline: 'Steady AI presence',
    monthlyPrice: 147,
    pagesPerMonth: 5,
    isMostPopular: false,
    ctaLabel: 'Start growing',
    expectedGrowth: '+50-80%',
    expectedGrowthLabel: 'traffic in 12 months',
    features: [
      '5 pages optimized for LLM recommendations',
      'Built for ChatGPT, Claude, Gemini, Perplexity + more',
      'Start appearing in AI answers',
      'New source of high-intent traffic'
    ],
    gradientColors: 'from-blue-100 to-blue-50',
    badgeColor: 'bg-blue-100 text-blue-900',
    badgeGradient: 'bg-blue-600'
  },
  growth: {
    id: 'growth',
    label: 'Growth',
    tagline: 'Rocket growth in AI',
    monthlyPrice: 497,
    pagesPerMonth: 20,
    isMostPopular: true,
    ctaLabel: 'Grow faster',
    expectedGrowth: '+150-250%',
    expectedGrowthLabel: 'traffic in 12 months',
    features: [
      '20 pages engineered for AI recommendations',
      'Fast visibility across ChatGPT, Claude, Gemini, Copilot & more',
      'Start getting recommended over competitors',
      'Measurable AI traffic within 3-6 months',
      'High-converting traffic — zero ad spend'
    ],
    gradientColors: 'from-emerald-100 to-emerald-50',
    badgeColor: 'bg-emerald-100 text-emerald-900',
    badgeGradient: 'bg-emerald-600'
  },
  scale: {
    id: 'scale',
    label: 'Scale',
    tagline: 'AI dominance',
    monthlyPrice: 997,
    pagesPerMonth: 50,
    isMostPopular: false,
    ctaLabel: 'Scale aggressively',
    expectedGrowth: '+400-600%',
    expectedGrowthLabel: 'traffic in 12 months',
    features: [
      '50 AI-optimized pages monthly',
      'Become the go-to source across all major AI platforms',
      'Maximum visibility in LLM recommendations',
      'Consistent flow of qualified leads'
    ],
    gradientColors: 'from-gray-100 to-gray-50',
    badgeColor: 'bg-gradient-to-r from-orange-400 to-red-500',
    badgeGradient: 'bg-gradient-to-r from-orange-400 to-red-500'
  }
}

/**
 * Calculate yearly price with discount
 * @param {number} monthlyPrice - Monthly price in USD
 * @param {number} discountPercent - Discount percentage (default 25%)
 * @returns {number} Discounted monthly price when billed annually
 */
export function getYearlyPrice(monthlyPrice, discountPercent = 25) {
  return Math.round(monthlyPrice * (1 - discountPercent / 100))
}

/**
 * Calculate yearly savings
 * @param {number} monthlyPrice - Monthly price in USD
 * @param {number} discountPercent - Discount percentage (default 25%)
 * @returns {number} Total savings per year
 */
export function getYearlySavings(monthlyPrice, discountPercent = 25) {
  const yearlyPrice = getYearlyPrice(monthlyPrice, discountPercent)
  return (monthlyPrice - yearlyPrice) * 12
}

/**
 * Format price for display
 * @param {number} price - Price in USD
 * @returns {string} Formatted price string (e.g., "$147/mo")
 */
export function formatPrice(price) {
  return `$${price}/mo`
}

// One-time full audit access price
export const AUDIT_UNLOCK_PRICE = 199
