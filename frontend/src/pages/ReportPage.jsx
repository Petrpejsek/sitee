import { useMemo, useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import EmailGate from '../components/EmailGate'
import UnlockModal from '../components/UnlockModal'
import LockOverlay from '../components/LockOverlay'
import { PRICING_PLANS, getYearlyPrice, getYearlySavings } from '../config/pricing'

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

function safeText(v, fallback) {
  if (v === null || v === undefined) return fallback
  const t = String(v).trim()
  if (!t || t === '-' || t === '—' || t.toLowerCase() === 'n/a') return fallback
  return t
}

function pctColor(score) {
  const s = Number(score)
  if (!Number.isFinite(s)) return 'gray'
  if (s >= 70) return 'green'
  if (s >= 40) return 'orange'
  return 'red'
}

function pillClass(color) {
  switch (color) {
    case 'green':
      return 'bg-green-50 text-green-800 border-green-200'
    case 'orange':
      return 'bg-orange-50 text-orange-800 border-orange-200'
    case 'red':
      return 'bg-red-50 text-red-800 border-red-200'
    default:
      return 'bg-gray-50 text-gray-800 border-gray-200'
  }
}

function Tooltip({ label, children }) {
  const [open, setOpen] = useState(false)
  return (
    <span className="relative inline-flex items-center">
      <span
        className="inline-flex items-center"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        tabIndex={0}
      >
        {children}
      </span>
      {open && (
        <span className="absolute z-50 top-full mt-2 w-64 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700 shadow-lg">
          {label}
        </span>
      )}
    </span>
  )
}

function LockedSection({ locked, children, onUnlock }) {
  if (!locked) return children
  return (
    <div className="relative">
      <div className="pointer-events-none select-none blur-sm">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-sm rounded-3xl border-2 border-gray-300 bg-white px-10 py-10 shadow-[0_20px_60px_rgba(0,0,0,0.15)]">
          
          <h2 className="mb-2 text-center text-2xl font-extrabold leading-tight tracking-tight text-gray-900">
            Your company is <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-600 to-orange-600">invisible</span> for GPT, Gemini, Perplexity etc.
          </h2>

          <p className="mb-8 text-center text-lg font-medium text-gray-700">
            AI sends traffic to <span className="font-bold text-blue-600">others.</span>
          </p>

          <button
            onClick={onUnlock}
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-4 text-lg font-bold text-white shadow-lg transition-all hover:from-blue-700 hover:to-blue-800 hover:shadow-xl active:scale-[0.97]"
          >
            Get AI traffic now
          </button>

        </div>
      </div>
    </div>
  )
}

function Section({ id, title, children }) {
  return (
    <section id={id} className="scroll-mt-24">
      <div className="mb-4 text-xs font-extrabold tracking-wider text-gray-500">{title}</div>
      {children}
    </section>
  )
}

function TrafficDistribution({ youPct, competitorsPct }) {
  const you = clamp(Number(youPct) || 0, 0, 100)
  const comp = clamp(Number(competitorsPct) || 0, 0, 100)
  const total = Math.max(1, you + comp)
  const youW = (you / total) * 100
  const compW = (comp / total) * 100

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="text-xs font-extrabold tracking-wider text-gray-500">AI TRAFFIC DISTRIBUTION</div>
      <div className="mt-2 text-2xl font-extrabold tracking-tight text-gray-900">AI answers →</div>

      <div className="mt-5 space-y-3">
        <div className="flex items-center justify-between gap-4 text-sm font-bold text-gray-900">
          <div className="shrink-0">Competitors</div>
          <div className="shrink-0 tabular-nums">{Math.round(comp)}%</div>
        </div>
        <div className="h-4 w-full overflow-hidden rounded-full bg-gray-200">
          <div className="h-full bg-gray-900" style={{ width: `${compW}%` }} />
        </div>

        <div className="flex items-center justify-between gap-4 text-sm font-bold text-gray-900">
          <div className="shrink-0">You</div>
          <div className="shrink-0 tabular-nums">{Math.round(you)}%</div>
        </div>
        <div className="h-4 w-full overflow-hidden rounded-full bg-gray-200">
          <div className="h-full bg-gray-400" style={{ width: `${youW}%` }} />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2 text-xs font-semibold text-gray-700">
        <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1">ChatGPT</span>
        <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1">Gemini</span>
        <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1">Perplexity</span>
      </div>
    </div>
  )
}

export default function ReportPage({ jobId }) {
  const { isAuthenticated, user } = useAuth()
  const [showEmailGate, setShowEmailGate] = useState(false)
  const [showUnlockModal, setShowUnlockModal] = useState(false)
  const [activeSection, setActiveSection] = useState('section_1')

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['report', jobId],
    queryFn: async () => {
      const res = await fetch(`/api/audit/${jobId}/report`, {
        credentials: 'include' // Include cookies for authentication
      })
      if (!res.ok) throw new Error('Failed to load report')
      return res.json()
    },
  })

  const meta = data?.meta || {}
  const raw = data?.raw || {}
  const normalized = data?.normalized || {}

  // Access control from backend
  const accessState = meta.access_state || 'preview'
  const isPreview = accessState === 'preview'
  const isLocked = accessState === 'locked'
  const isUnlocked = accessState === 'unlocked'
  const lockedSections = new Set(meta.locked_sections || [])
  const canUnlock = meta.can_unlock || false
  
  // Helper: Check if detailed content should be locked
  // For LOCKED state: show teaser (20-30%), lock details (70-80%)
  const isDetailLocked = isLocked || isPreview
  const shouldShowDetails = isUnlocked
  
  // Show email gate for anonymous users after scrolling past first section
  useEffect(() => {
    if (isPreview && !isAuthenticated && !showEmailGate) {
      const handleScroll = () => {
        const scrollPosition = window.scrollY
        if (scrollPosition > 800) {
          setShowEmailGate(true)
        }
      }
      window.addEventListener('scroll', handleScroll)
      return () => window.removeEventListener('scroll', handleScroll)
    }
  }, [isPreview, isAuthenticated, showEmailGate])
  
  const onUnlock = () => {
    if (canUnlock) {
      setShowUnlockModal(true)
    } else if (!isAuthenticated) {
      setShowEmailGate(true)
    }
  }

  const core = raw?.core_audit || {}
  const isSalesV2 = Boolean(core?.stage_1_ai_visibility)
  const isSalesV1 = Boolean(core?.stage_a_visibility)

  // Sales schema (V2)
  const vis2 = core?.stage_1_ai_visibility || {}
  const aiInterp = core?.ai_interpretation || {}
  const decisionAudit = Array.isArray(core?.decision_readiness_audit) && core.decision_readiness_audit.length > 0
    ? core.decision_readiness_audit
    : [
        { element_name: "Pricing information", category: "Comparability", status: "missing", why_critical: "Buyers need price ranges to compare" },
        { element_name: "Service definitions", category: "Decision Clarity", status: "weak", why_critical: "AI needs scope boundaries" },
        { element_name: "Customer testimonials", category: "Trust & Authority", status: "missing", why_critical: "Social proof builds confidence" },
        { element_name: "Use case examples", category: "Entity Understanding", status: "weak", why_critical: "Contextual relevance" },
        { element_name: "Process/how it works", category: "Decision Clarity", status: "missing", why_critical: "Operational clarity" },
        { element_name: "Delivery timelines", category: "Risk Reduction", status: "weak", why_critical: "Expectation management" },
        { element_name: "Industry specialization", category: "Entity Understanding", status: "missing", why_critical: "Expertise positioning" },
        { element_name: "Guarantees/warranties", category: "Risk Reduction", status: "missing", why_critical: "Risk mitigation" },
        { element_name: "Comparison to alternatives", category: "Comparability", status: "weak", why_critical: "Competitive positioning" },
        { element_name: "Success metrics/outcomes", category: "Trust & Authority", status: "missing", why_critical: "Outcome validation" },
        { element_name: "Support/service level", category: "Risk Reduction", status: "weak", why_critical: "Post-purchase confidence" },
        { element_name: "Technical requirements", category: "Decision Clarity", status: "missing", why_critical: "Implementation clarity" }
      ]
  const decisionScore = core?.decision_coverage_score || {
    present: decisionAudit.filter(e => e?.status === 'present').length,
    weak: decisionAudit.filter(e => e?.status === 'weak').length,
    missing: decisionAudit.filter(e => e?.status === 'missing').length,
    total: decisionAudit.length
  }
  
  // AI Requirements: Support both old (ai_requirements) and new (ai_requirements_before/after) formats
  const aiRequirementsBefore = Array.isArray(core?.ai_requirements_before) && core.ai_requirements_before.length > 0 
    ? core.ai_requirements_before 
    : [
        { requirement_name: "Pricing transparency", category: "Comparability", why_ai_needs_this: "AI needs clear pricing to compare value", current_status: "missing", impact_if_missing: "AI defaults to competitors" },
        { requirement_name: "Service definitions", category: "Decision Clarity", why_ai_needs_this: "AI needs scope clarity", current_status: "missing", impact_if_missing: "AI cannot explain offerings" },
        { requirement_name: "Customer proof", category: "Trust & Authority", why_ai_needs_this: "AI needs social validation", current_status: "weak", impact_if_missing: "Lower recommendation confidence" },
        { requirement_name: "Process clarity", category: "Decision Clarity", why_ai_needs_this: "AI needs operational understanding", current_status: "weak", impact_if_missing: "Cannot guide users" },
        { requirement_name: "Use case examples", category: "Entity Understanding", why_ai_needs_this: "AI needs context for recommendations", current_status: "missing", impact_if_missing: "Generic recommendations only" },
        { requirement_name: "Delivery timelines", category: "Risk Reduction", why_ai_needs_this: "AI needs expectation setting", current_status: "missing", impact_if_missing: "Cannot address timing concerns" },
        { requirement_name: "Differentiators", category: "Comparability", why_ai_needs_this: "AI needs unique value props", current_status: "weak", impact_if_missing: "Commodity positioning" },
        { requirement_name: "Industry focus", category: "Entity Understanding", why_ai_needs_this: "AI needs specialization signals", current_status: "missing", impact_if_missing: "Generic positioning" },
        { requirement_name: "Success metrics", category: "Trust & Authority", why_ai_needs_this: "AI needs outcome proof", current_status: "missing", impact_if_missing: "No credibility boost" },
        { requirement_name: "Support clarity", category: "Risk Reduction", why_ai_needs_this: "AI needs risk mitigation", current_status: "weak", impact_if_missing: "Higher perceived risk" }
      ]
  const aiRequirementsAfter = Array.isArray(core?.ai_requirements_after) && core.ai_requirements_after.length > 0
    ? core.ai_requirements_after
    : [
        { requirement_name: "Pricing transparency", category: "Comparability", what_must_be_built: "Add pricing tiers with value anchors", ai_outcome_unlocked: "AI can recommend based on budget" },
        { requirement_name: "Service definitions", category: "Decision Clarity", what_must_be_built: "Create clear service scope pages", ai_outcome_unlocked: "AI explains offerings confidently" },
        { requirement_name: "Customer proof", category: "Trust & Authority", what_must_be_built: "Add case studies with metrics", ai_outcome_unlocked: "Higher recommendation confidence" },
        { requirement_name: "Process clarity", category: "Decision Clarity", what_must_be_built: "Document step-by-step process", ai_outcome_unlocked: "AI guides users through journey" },
        { requirement_name: "Use case examples", category: "Entity Understanding", what_must_be_built: "Create industry-specific examples", ai_outcome_unlocked: "Targeted recommendations" },
        { requirement_name: "Delivery timelines", category: "Risk Reduction", what_must_be_built: "Add timeline expectations", ai_outcome_unlocked: "AI addresses timing concerns" },
        { requirement_name: "Differentiators", category: "Comparability", what_must_be_built: "Highlight unique value", ai_outcome_unlocked: "Premium positioning" },
        { requirement_name: "Industry focus", category: "Entity Understanding", what_must_be_built: "Showcase specialization", ai_outcome_unlocked: "Expert positioning" },
        { requirement_name: "Success metrics", category: "Trust & Authority", what_must_be_built: "Add outcome data", ai_outcome_unlocked: "Credibility boost" },
        { requirement_name: "Support clarity", category: "Risk Reduction", what_must_be_built: "Define support options", ai_outcome_unlocked: "Lower perceived risk" }
      ]
  const aiRequirementsLegacy = Array.isArray(core?.ai_requirements) ? core.ai_requirements : []
  
  // Merge before/after into single array for rendering (with type marker)
  const aiRequirements = [
    ...aiRequirementsBefore.map(r => ({ ...r, _type: 'before' })),
    ...aiRequirementsAfter.map(r => ({ ...r, _type: 'after' })),
    // Fallback to legacy format if new format is empty
    ...(aiRequirementsBefore.length === 0 && aiRequirementsAfter.length === 0 ? aiRequirementsLegacy : [])
  ]
  
  const reasons2 = Array.isArray(core?.stage_2_why_ai_chooses_others) ? core.stage_2_why_ai_chooses_others : []
  const needs2 = Array.isArray(core?.stage_3_what_ai_needs) ? core.stage_3_what_ai_needs : []
  const packages2 = core?.stage_4_packages || {}
  const impact2 = core?.stage_5_business_impact || {}
  const appendix = core?.appendix || {}
  const evidenceLayer = core?.evidence_layer || {}
  const company = evidenceLayer?.company_profile || {}
  const evidenceItems = Array.isArray(evidenceLayer?.evidence) ? evidenceLayer.evidence : []

  // Sales schema (V1 - legacy in this repo)
  const vis1 = core?.stage_a_visibility || {}
  const blockers1 = Array.isArray(core?.stage_b_blockers) ? core.stage_b_blockers : []
  const needs1 = Array.isArray(core?.stage_c_content_needs) ? core.stage_c_content_needs : []
  const packages1 = core?.stage_d_packages || {}
  const decision1 = core?.stage_e_recommendation || {}

  // Legacy fallbacks (older jobs)
  const legacyScores = core?.scores || {}
  const legacyGaps = Array.isArray(core?.top_gaps) ? core.top_gaps : []
  const legacyRisks = Array.isArray(core?.llm_visibility_risks) ? core.llm_visibility_risks : []

  const coverageLevels = normalized?.coverage_levels || {}
  const gp = normalized?.growth_plan_summary || {}

  const onRerun = async () => {
    await fetch(`/api/audit/${jobId}/rerun`, { method: 'POST' })
    await refetch()
  }

  const scrollTo = (id) => {
    const el = document.getElementById(id)
    if (el) {
      const headerHeight = 140 // Height of sticky header
      const elementPosition = el.getBoundingClientRect().top + window.pageYOffset
      const offsetPosition = elementPosition - headerHeight
      
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      })
    }
  }

  // Track active section on scroll
  useEffect(() => {
    const handleScroll = () => {
      const sections = ['section_1', 'section_2', 'section_3', 'section_4', 'section_5', 'section_6']
      const viewportMiddle = window.innerHeight / 2
      
      // Find which section contains the middle of the viewport
      let activeId = 'section_1'
      
      for (let i = sections.length - 1; i >= 0; i--) {
        const id = sections[i]
        const el = document.getElementById(id)
        if (el) {
          const rect = el.getBoundingClientRect()
          
          // If viewport middle is within this section
          if (rect.top <= viewportMiddle && rect.bottom >= viewportMiddle) {
            activeId = id
            break
          }
        }
      }
      
      setActiveSection(activeId)
    }
    
    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll() // Initial check
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // NOTE: Hooks must be called before any conditional returns (loading/error).
  const youShare = useMemo(() => {
    const a = Number(vis2?.chatgpt_visibility_percent)
    const b = Number(vis2?.gemini_visibility_percent)
    const c = Number(vis2?.perplexity_visibility_percent)
    const vals = [a, b, c].filter((x) => Number.isFinite(x))
    if (!vals.length) return 22
    return clamp(Math.round(vals.reduce((s, x) => s + x, 0) / vals.length), 0, 100)
  }, [vis2?.chatgpt_visibility_percent, vis2?.gemini_visibility_percent, vis2?.perplexity_visibility_percent])

  const competitorShare = 100 - youShare

  // Group AI requirements by category
  const requirementsByCategory = useMemo(() => {
    if (!aiRequirements.length) return {}
    
    const groups = {
      decision_clarity: [],
      comparability: [],
      trust_authority: [],
      entity_understanding: [],
      risk_confidence: []
    }
    
    for (const req of aiRequirements) {
      const cat = req?.category
      if (cat && groups[cat]) {
        groups[cat].push(req)
      }
    }
    
    return groups
  }, [aiRequirements])

  const categoryLabels = {
    decision_clarity: 'Decision Clarity',
    comparability: 'Comparability',
    trust_authority: 'Trust & Authority',
    entity_understanding: 'Entity Understanding',
    risk_confidence: 'Risk & Confidence'
  }

  const resolveEvidence = (refs) => {
    if (!Array.isArray(refs) || !evidenceItems.length) return []
    const out = []
    for (const id of refs) {
      const n = Number(id)
      if (!Number.isFinite(n)) continue
      const idx = Math.trunc(n)
      if (idx < 0 || idx >= evidenceItems.length) continue
      out.push(evidenceItems[idx])
      if (out.length >= 2) break
    }
    return out
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
            <div className="h-6 w-48 animate-pulse rounded bg-gray-200" />
            <div className="mt-6 h-24 w-full animate-pulse rounded bg-gray-100" />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="mx-auto max-w-3xl px-4 py-16">
          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
            <div className="text-lg font-bold text-gray-900">Error</div>
            <div className="mt-2 text-sm text-gray-600">{error.message}</div>
            <button
              onClick={() => window.location.assign('/')}
              className="mt-6 rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Back
            </button>
          </div>
        </div>
      </div>
    )
  }

  const statusColor = isSalesV2
    ? pctColor(vis2?.chatgpt_visibility_percent)
    : isSalesV1
      ? pctColor(vis1?.chatgpt_visibility_percent)
      : pctColor(legacyScores?.recommendability)
  const statusLabel = statusColor === 'green' ? 'Strong' : statusColor === 'orange' ? 'Limited' : 'Poor'

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* GLOBAL TOP BAR (STICKY) - AUDIT IDENTITY */}
      <div className="sticky top-0 z-40 border-b-2 border-gray-200 bg-white/95 backdrop-blur shadow-sm">
        <div className="mx-auto max-w-6xl px-4 py-4">
          {/* TOP ROW: Logo + Identity + Status */}
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            {/* LEFT: Audit identity */}
            <div className="flex items-center gap-8">
              {/* sitee.ai Logo - EXACT PNG */}
              <img 
                src="/sitee-logo.png" 
                alt="sitee.ai" 
                className="h-[88px] w-auto shrink-0"
              />
              
              <div className="min-w-0 space-y-2">
                <div className="text-base font-bold text-gray-700">
                  Audit prepared for: <span className="font-black text-gray-900">{meta.domain || 'Unknown'}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold uppercase tracking-wider text-gray-600">Current status:</span>
                  <span className={`inline-flex items-center gap-1.5 rounded-full border-2 px-3 py-1 text-xs font-bold ${
                    statusColor === 'green' ? 'border-green-200 bg-green-50 text-green-900' :
                    statusColor === 'orange' ? 'border-orange-200 bg-orange-50 text-orange-900' :
                    'border-red-200 bg-red-50 text-red-900'
                  }`}>
                    {statusLabel} visibility
                  </span>
                </div>
              </div>
            </div>

            {/* RIGHT: CTA + Update button */}
            <div className="flex items-center gap-3 shrink-0">
              {/* Main CTA - scrolls to sales section */}
              <button
                onClick={() => scrollTo('section_6')}
                className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-emerald-700 transition-colors"
              >
                {activeSection === 'section_6' ? "Get My Growth Plan" : 'Start Growing Your Traffic'}
              </button>
              
              {/* Update button (unlocked only) */}
              {isUnlocked && (
                <button
                  onClick={onRerun}
                  className="rounded-lg border-2 border-gray-300 bg-white px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50"
                >
                  {isFetching ? 'Updating…' : 'Update report'}
                </button>
              )}
            </div>
          </div>

          {/* BOTTOM ROW: Single-line audit navigation menu */}
          <nav className="mt-4 flex items-center gap-1 border-t border-gray-200 pt-3 text-xs font-bold">
            <button
              onClick={() => scrollTo('section_1')}
              className={`px-3 py-1.5 transition-colors ${
                activeSection === 'section_1'
                  ? 'text-red-900 border-b-2 border-red-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              01 Position
            </button>
            <span className="text-gray-300">•</span>
            <button
              onClick={() => scrollTo('section_2')}
              className={`px-3 py-1.5 transition-colors ${
                activeSection === 'section_2'
                  ? 'text-gray-900 border-b-2 border-gray-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              02 Interpretation
            </button>
            <span className="text-gray-300">•</span>
            <button
              onClick={() => scrollTo('section_3')}
              className={`px-3 py-1.5 transition-colors ${
                activeSection === 'section_3'
                  ? 'text-red-900 border-b-2 border-red-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              03 Barriers
            </button>
            <span className="text-gray-300">•</span>
            <button
              onClick={() => scrollTo('section_4')}
              className={`px-3 py-1.5 transition-colors ${
                activeSection === 'section_4'
                  ? 'text-gray-900 border-b-2 border-gray-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              04 Criteria
            </button>
            <span className="text-gray-300">•</span>
            <button
              onClick={() => scrollTo('section_5')}
              className={`px-3 py-1.5 transition-colors ${
                activeSection === 'section_5'
                  ? 'text-red-900 border-b-2 border-red-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              05 Cost
            </button>
            <span className="text-gray-300">•</span>
            <button
              onClick={() => scrollTo('section_6')}
              className={`px-3 py-1.5 transition-colors ${
                activeSection === 'section_6'
                  ? 'text-emerald-900 border-b-2 border-emerald-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              06 Solution
            </button>
          </nav>
        </div>
      </div>

      {/* SECTION 1: YOUR CURRENT POSITION */}
      <div className="w-full border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <Section id="section_1" title="01. YOUR CURRENT POSITION IN AI SYSTEMS">
            {!isSalesV2 && (
              <div className="mb-4 rounded-2xl border border-orange-200 bg-orange-50 p-5 text-sm text-orange-900 shadow-sm">
                This report is using a legacy schema. Re-run the audit to generate the new AI Visibility Sales dashboard output.
              </div>
            )}

            {/* BIG NUMBER + HEADLINE (SAME AS OTHER SECTIONS 02-07) */}
            <div className="mb-8 flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-4 border-red-600 bg-red-600 text-2xl font-black text-white shadow-lg">
                01
              </div>
              <div>
                <div className="text-3xl font-extrabold tracking-tight text-gray-900">
                  Your current position in AI systems
                </div>
                <div className="mt-1 inline-flex items-center gap-2 rounded-full border-2 border-red-600 bg-red-50 px-3 py-1">
                  <span className="text-xl">🔴</span>
                  <span className="text-sm font-black text-red-900">
                    {statusColor === 'red' ? 'Poor' : statusColor === 'orange' ? 'Limited' : 'Strong'} AI Visibility
                  </span>
                </div>
              </div>
            </div>

            {/* TWO COLUMNS: WHY AI FAILS (left) + MODEL STATUS (right) */}
            <div className="grid gap-8 md:grid-cols-2">
              
              {/* LEFT COLUMN - WHAT AI EXPECTS BUT YOUR SITE LACKS */}
              <div className="space-y-6">
                <div>
                  <div className="text-xl font-extrabold text-gray-900">
                    What AI expects from a recommendable website
                  </div>
                  <div className="mt-1 text-sm font-semibold text-gray-600">
                    (Missing on your website)
                  </div>
                </div>

                {/* CHECKLIST - what's missing */}
                <div className="space-y-3">
                  <div className="flex items-start gap-3 rounded-lg border-2 border-red-200 bg-red-50 p-3">
                    <span className="text-xl shrink-0">❌</span>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Clear service explanation pages</div>
                      <div className="mt-1 text-xs font-semibold text-gray-700">AI cannot understand what you offer or how it works.</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border-2 border-red-200 bg-red-50 p-3">
                    <span className="text-xl shrink-0">❌</span>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Question–answer content</div>
                      <div className="mt-1 text-xs font-semibold text-gray-700">No FAQ blocks that AI can quote directly in responses.</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border-2 border-orange-200 bg-orange-50 p-3">
                    <span className="text-xl shrink-0">❌</span>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Pricing & value tables</div>
                      <div className="mt-1 text-xs font-semibold text-gray-700">Missing structured pricing that AI can compare with alternatives.</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border-2 border-orange-200 bg-orange-50 p-3">
                    <span className="text-xl shrink-0">❌</span>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Comparison pages</div>
                      <div className="mt-1 text-xs font-semibold text-gray-700">No content showing how you differ from alternatives.</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border-2 border-orange-200 bg-orange-50 p-3">
                    <span className="text-xl shrink-0">❌</span>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Decision guidance content</div>
                      <div className="mt-1 text-xs font-semibold text-gray-700">AI cannot determine who your service is best suited for.</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border-2 border-orange-200 bg-orange-50 p-3">
                    <span className="text-xl shrink-0">❌</span>
                    <div>
                      <div className="text-sm font-bold text-gray-900">Clear entity & trust signals</div>
                      <div className="mt-1 text-xs font-semibold text-gray-700">Weak authority signals make AI hesitant to recommend you.</div>
                    </div>
                  </div>
                </div>

                <div className="text-sm font-semibold text-gray-600">
                  Without these elements, AI systems avoid using a website as a source.
                </div>

                {/* PROBLEM BOX (smaller, less dominant) */}
                <div className="rounded-xl border border-red-600 bg-red-50 p-4">
                  <div className="text-xs font-bold uppercase text-red-900">Problem detected</div>
                  <div className="mt-1 text-sm font-bold text-gray-900">
                    {safeText(
                      isSalesV2 ? vis2?.hard_sentence : isSalesV1 ? vis1?.hard_sentence : null,
                      'AI systems actively recommend competitors instead of your business.'
                    )}
                  </div>
                </div>

                {/* Company snapshot - COLLAPSIBLE */}
                <details open className="rounded-2xl border border-gray-200 bg-gray-50">
                  <summary className="cursor-pointer px-5 py-4 text-xs font-black uppercase tracking-wider text-gray-600 hover:bg-gray-100">
                    Technical appendix: Company snapshot
                  </summary>
                  <div className="border-t border-gray-200 p-5 space-y-2 text-sm font-semibold text-gray-700">
                    <div>
                      <span className="font-black text-gray-800">Business:</span>{' '}
                      {safeText(company?.company_name, meta.domain || 'this domain')}
                    </div>
                    <div>
                      <span className="font-black text-gray-800">Primary offer:</span>{' '}
                      {safeText(company?.primary_offer_summary, 'Not clearly detected')}
                    </div>
                    {Array.isArray(company?.locations_detected) && company.locations_detected.length > 0 && (
                      <div>
                        <span className="font-black text-gray-800">Locations:</span> {company.locations_detected.slice(0, 2).join(', ')}
                      </div>
                    )}
                    <div>
                      <span className="font-black text-gray-800">Language:</span> {safeText(company?.primary_language_detected, 'not detected')}
                    </div>
                    <div className="mt-3 text-xs text-gray-500">
                      Analyzed {Number(appendix?.pages_analyzed_target ?? meta.pages_analyzed ?? 0) || 0} pages
                    </div>
                  </div>
                </details>
              </div>

              {/* RIGHT COLUMN - MODEL LAYER WITH PROGRESS BARS */}
              <div className="space-y-4">
                <div>
                  <div className="text-xl font-extrabold text-gray-900">
                    AI systems influencing customer decisions (US)
                  </div>
                  <div className="mt-2 text-sm font-semibold text-gray-600">
                    AI confidence to recommend your business
                  </div>
                </div>

                {/* MODEL-BY-MODEL STATUS WITH PROGRESS BARS */}
                <div className="space-y-3">
                  {/* ChatGPT */}
                  <div className="rounded-xl border-2 border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-base font-black text-gray-900">ChatGPT</div>
                      </div>
                      <div className={`rounded-full px-2 py-1 text-xs font-black ${
                        (isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) >= 70
                          ? 'bg-green-100 text-green-900'
                          : (isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) >= 40
                            ? 'bg-orange-100 text-orange-900'
                            : 'bg-red-100 text-red-900'
                      }`}>
                        {(isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) >= 70
                          ? '🟢'
                          : (isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) >= 40
                            ? '🟠'
                            : '🔴'}
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div 
                        className={`h-full ${
                          (isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) >= 70
                            ? 'bg-green-600'
                            : (isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) >= 40
                              ? 'bg-orange-500'
                              : 'bg-red-600'
                        }`}
                        style={{ width: `${Math.max(5, (isSalesV2 ? vis2?.chatgpt_visibility_percent : isSalesV1 ? vis1?.chatgpt_visibility_percent : 0) || 5)}%` }}
                      />
                    </div>
                    <div className="text-xs font-bold text-gray-700">
                      {safeText(isSalesV2 ? vis2?.chatgpt_label : isSalesV1 ? vis1?.chatgpt_label : null, 'Not recommending')}
                    </div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      No structured service explanations detected
                    </div>
                  </div>

                  {/* Google Gemini */}
                  <div className="rounded-xl border-2 border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-base font-black text-gray-900">Google Gemini <span className="text-xs font-normal text-gray-500">(AI Overviews)</span></div>
                      </div>
                      <div className={`rounded-full px-2 py-1 text-xs font-black ${
                        (isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) >= 70
                          ? 'bg-green-100 text-green-900'
                          : (isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) >= 40
                            ? 'bg-orange-100 text-orange-900'
                            : 'bg-red-100 text-red-900'
                      }`}>
                        {(isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) >= 70
                          ? '🟢'
                          : (isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) >= 40
                            ? '🟠'
                            : '🔴'}
                      </div>
                    </div>
                    <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div 
                        className={`h-full ${
                          (isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) >= 70
                            ? 'bg-green-600'
                            : (isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) >= 40
                              ? 'bg-orange-500'
                              : 'bg-red-600'
                        }`}
                        style={{ width: `${Math.max(5, (isSalesV2 ? vis2?.gemini_visibility_percent : isSalesV1 ? vis1?.gemini_visibility_percent : 0) || 5)}%` }}
                      />
                    </div>
                    <div className="text-xs font-bold text-gray-700">
                      {safeText(isSalesV2 ? vis2?.gemini_label : isSalesV1 ? vis1?.gemini_label : null, 'Low visibility')}
                    </div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      No clear entity & service pages
                    </div>
                  </div>

                  {/* Perplexity */}
                  <div className="rounded-xl border-2 border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-base font-black text-gray-900">Perplexity</div>
                      </div>
                      <div className={`rounded-full px-2 py-1 text-xs font-black ${
                        (isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) >= 70
                          ? 'bg-green-100 text-green-900'
                          : (isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) >= 40
                            ? 'bg-orange-100 text-orange-900'
                            : 'bg-red-100 text-red-900'
                      }`}>
                        {(isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) >= 70
                          ? '🟢'
                          : (isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) >= 40
                            ? '🟠'
                            : '🔴'}
                      </div>
                    </div>
                    <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div 
                        className={`h-full ${
                          (isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) >= 70
                            ? 'bg-green-600'
                            : (isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) >= 40
                              ? 'bg-orange-500'
                              : 'bg-red-600'
                        }`}
                        style={{ width: `${Math.max(5, (isSalesV2 ? vis2?.perplexity_visibility_percent : isSalesV1 ? vis1?.perplexity_visibility_percent : 0) || 5)}%` }}
                      />
                    </div>
                    <div className="text-xs font-bold text-gray-700">
                      {safeText(isSalesV2 ? vis2?.perplexity_label : isSalesV1 ? vis1?.perplexity_label : null, 'Not cited')}
                    </div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      No quotable or reference-style pages
                    </div>
                  </div>

                  {/* Microsoft Copilot */}
                  <div className="rounded-xl border-2 border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-base font-black text-gray-900">Microsoft Copilot</div>
                      </div>
                      <div className="rounded-full bg-orange-100 px-2 py-1 text-xs font-black text-orange-900">
                        🟠
                      </div>
                    </div>
                    <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div className="h-full bg-orange-500" style={{ width: '30%' }} />
                    </div>
                    <div className="text-xs font-bold text-gray-700">Estimated: Weak presence</div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      Inconsistent business signals
                    </div>
                  </div>

                  {/* Claude */}
                  <div className="rounded-xl border-2 border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-base font-black text-gray-900">Claude</div>
                      </div>
                      <div className="rounded-full bg-orange-100 px-2 py-1 text-xs font-black text-orange-900">
                        🟠
                      </div>
                    </div>
                    <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div className="h-full bg-orange-500" style={{ width: '25%' }} />
                    </div>
                    <div className="text-xs font-bold text-gray-700">Estimated: Limited confidence</div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      Fragmented content structure
                    </div>
                  </div>

                  {/* Grok */}
                  <div className="rounded-xl border-2 border-gray-200 bg-white p-4 shadow-sm">
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="text-base font-black text-gray-900">Grok <span className="text-xs font-normal text-gray-500">(xAI)</span></div>
                      </div>
                      <div className="rounded-full bg-orange-100 px-2 py-1 text-xs font-black text-orange-900">
                        🟠
                      </div>
                    </div>
                    <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                      <div className="h-full bg-orange-500" style={{ width: '20%' }} />
                    </div>
                    <div className="text-xs font-bold text-gray-700">Estimated: Emerging / not visible</div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      No structured real-time context
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                  <div className="text-xs font-bold uppercase text-gray-500">Note</div>
                  <div className="mt-1 text-xs font-semibold text-gray-600">
                    Progress bars represent structural confidence estimates.
                  </div>
                </div>
              </div>
            </div>

            {/* SUMMARY / VERDICT LINE */}
            <div className="mt-8 rounded-2xl border-2 border-red-600 bg-red-50 p-6 shadow-md">
              <div className="flex items-start gap-4">
                <div className="text-3xl">🔴</div>
                <div>
                  <div className="text-sm font-black uppercase tracking-wider text-red-900">Summary</div>
                  <div className="mt-2 text-lg font-extrabold text-gray-900">
                    At this moment, AI systems do not consider your website a reliable source for recommendations.
                  </div>
                </div>
              </div>
            </div>
          </Section>
        </div>
      </div>

      {/* SECTION 2: HOW AI CURRENTLY INTERPRETS YOUR BUSINESS */}
      <div className="w-full border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <Section id="section_2" title="02. INTERPRETATION">
            {/* BIG NUMBER + HEADLINE + STATUS BADGE */}
            <div className="mb-8 flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-4 border-orange-500 bg-orange-500 text-2xl font-black text-white shadow-lg">
                02
              </div>
              <div>
                <div className="text-3xl font-extrabold tracking-tight text-gray-900">
                  How AI currently interprets your business
                </div>
                <div className="mt-1 inline-flex items-center gap-2 rounded-full border-2 border-orange-500 bg-orange-50 px-3 py-1">
                  <span className="text-xl">⚠️</span>
                  <span className="text-sm font-black text-orange-900">
                    {aiInterp?.confidence === 'strong' ? 'Strong understanding' : aiInterp?.confidence === 'partial' ? 'Partial understanding' : 'Shallow understanding'}
                  </span>
                </div>
              </div>
            </div>

            {/* OPPORTUNITY TEASER */}
            {isDetailLocked && (
              <div className="mb-6 rounded-xl border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50 p-4">
                <div className="text-sm font-bold text-gray-900">
                  💡 AI interpretation analysis reveals major gaps in how ChatGPT & Gemini understand your business
                </div>
                <div className="mt-2 text-xs text-gray-700 font-medium">
                  See exactly what's missing and how fixing it opens up consistent AI recommendations.
                </div>
              </div>
            )}

            {/* TWO-BLOCK LAYOUT: LEFT (What AI thinks) + RIGHT (What AI is missing) */}
            <LockedSection locked={lockedSections.has('section_2_details')} onUnlock={onUnlock}>
            <div className="grid gap-8 md:grid-cols-2">
              
              {/* LEFT BLOCK: WHAT AI THINKS YOU ARE */}
              <div className="space-y-6">
                <div>
                  <div className="text-xl font-extrabold text-gray-900">
                    What AI thinks you are
                  </div>
                  <div className="mt-1 text-xs font-bold uppercase tracking-wider text-gray-500">
                    AI-level interpretation (simplified)
                  </div>
                </div>

                {/* AI's simplified understanding - marked as REDUCED */}
                <div className="rounded-2xl border-2 border-orange-300 bg-orange-50 p-6 shadow-sm">
                  <div className="text-sm font-bold text-orange-900">
                    AI reduces your business to the following simplified description:
                  </div>
                  <div className="mt-4 rounded-lg border-2 border-orange-400 bg-white p-4 shadow-inner">
                    <div className="text-base font-bold text-gray-900 break-words italic">
                      {safeText(
                        aiInterp?.summary, 
                        safeText(company?.primary_offer_summary, 'A business with unclear positioning and limited quotable information.')
                      )}
                    </div>
                  </div>
                  <div className="mt-4 rounded-lg border border-orange-300 bg-orange-100 p-3">
                    <div className="text-xs font-bold text-orange-900">
                      ⚠️ This interpretation ignores decision-making context.
                    </div>
                  </div>
                </div>

                {/* SERVICE TAGS - moved here with weak signal indicator */}
                {Array.isArray(aiInterp?.detected_signals) && aiInterp.detected_signals.length > 0 ? (
                  <div>
                    <div className="text-sm font-bold text-gray-800">
                      Signals AI currently recognizes
                    </div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      Weak / generic signals
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {aiInterp.detected_signals.slice(0, 8).map((signal, i) => (
                        <span key={i} className="rounded-full border-2 border-orange-200 bg-orange-50 px-3 py-1 text-xs font-bold text-orange-800">
                          {signal}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (Array.isArray(company?.services_detected) && company.services_detected.length > 0) && (
                  <div>
                    <div className="text-sm font-bold text-gray-800">
                      Signals AI currently recognizes
                    </div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      Weak / generic signals
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {company.services_detected.slice(0, 5).map((service, i) => (
                        <span key={i} className="rounded-full border-2 border-orange-200 bg-orange-50 px-3 py-1 text-xs font-bold text-orange-800">
                          {service}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* RIGHT BLOCK: WHAT AI IS MISSING */}
              <div className="space-y-6">
                <div>
                  <div className="text-xl font-extrabold text-gray-900">
                    What AI is missing
                  </div>
                  <div className="mt-1 text-xs font-bold uppercase tracking-wider text-gray-500">
                    Critical understanding gaps
                  </div>
                </div>

                {/* CAUSAL FRAMING - make it clear why this matters */}
                <div className="rounded-lg border-2 border-red-600 bg-red-50 p-4">
                  <div className="text-sm font-black text-red-900">
                    These missing elements prevent AI from making a recommendation decision.
                  </div>
                </div>

                {/* BULLET LIST - what AI doesn't understand */}
                <div className="rounded-2xl border-2 border-gray-300 bg-gray-50 p-6 shadow-sm">
                  <ul className="space-y-4">
                    {Array.isArray(aiInterp?.missing_elements) && aiInterp.missing_elements.length > 0 ? (
                      aiInterp.missing_elements.map((elem, i) => (
                        <li key={i} className="flex items-start gap-3">
                          <span className="text-xl shrink-0 mt-0.5">{elem?.severity === 'critical' ? '🔴' : '❌'}</span>
                          <div>
                            <div className="text-sm font-bold text-gray-900">{elem?.label || 'Missing element'}</div>
                            <div className="mt-1 text-xs font-semibold text-gray-600">
                              {elem?.impact || 'Limits AI recommendation confidence'}
                            </div>
                          </div>
                        </li>
                      ))
                    ) : (
                      <>
                        <li className="flex items-start gap-3">
                          <span className="text-xl shrink-0 mt-0.5">❌</span>
                          <div>
                            <div className="text-sm font-bold text-gray-900">No clear service differentiation</div>
                            <div className="mt-1 text-xs font-semibold text-gray-600">
                              AI cannot explain how you differ from alternatives
                            </div>
                          </div>
                        </li>
                        <li className="flex items-start gap-3">
                          <span className="text-xl shrink-0 mt-0.5">❌</span>
                          <div>
                            <div className="text-sm font-bold text-gray-900">No decision-making context</div>
                            <div className="mt-1 text-xs font-semibold text-gray-600">
                              AI cannot determine who this is best for or why
                            </div>
                          </div>
                        </li>
                        <li className="flex items-start gap-3">
                          <span className="text-xl shrink-0 mt-0.5">❌</span>
                          <div>
                            <div className="text-sm font-bold text-gray-900">No pricing or value structure</div>
                            <div className="mt-1 text-xs font-semibold text-gray-600">
                              AI cannot compare you to competitors on value
                            </div>
                          </div>
                        </li>
                        <li className="flex items-start gap-3">
                          <span className="text-xl shrink-0 mt-0.5">❌</span>
                          <div>
                            <div className="text-sm font-bold text-gray-900">No comparison or alternatives</div>
                            <div className="mt-1 text-xs font-semibold text-gray-600">
                              No content showing trade-offs or competitive position
                            </div>
                          </div>
                        </li>
                        <li className="flex items-start gap-3">
                          <span className="text-xl shrink-0 mt-0.5">❌</span>
                          <div>
                            <div className="text-sm font-bold text-gray-900">No audience fit (who it's for / not for)</div>
                            <div className="mt-1 text-xs font-semibold text-gray-600">
                              AI cannot guide customers on whether this fits their needs
                            </div>
                          </div>
                        </li>
                      </>
                    )}
                  </ul>
                </div>
              </div>
            </div>

            {/* IMPLICATIONS PANEL - ANALYTICAL, NOT EMOTIONAL */}
            <div className="mt-8 rounded-2xl border-2 border-gray-300 bg-gray-50 p-6 shadow-sm">
              <div className="text-xs font-black uppercase tracking-wider text-gray-600">
                Practical implications of this interpretation
              </div>
              <ul className="mt-4 space-y-3 text-sm font-semibold text-gray-800">
                <li className="flex items-start gap-3">
                  <span className="shrink-0 text-gray-400">•</span>
                  <span>AI recognizes branding signals, not service logic</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="shrink-0 text-gray-400">•</span>
                  <span>AI extracts descriptions, not decision frameworks</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="shrink-0 text-gray-400">•</span>
                  <span>AI cannot translate this information into recommendations</span>
                </li>
              </ul>
            </div>

            {/* KEY MESSAGE / TAKEAWAY BOX - HARDENED */}
            <div className="mt-8 rounded-2xl border-2 border-red-600 bg-red-50 p-6 shadow-md">
              <div className="flex items-start gap-4">
                <div className="text-3xl">⚠️</div>
                <div>
                  <div className="text-sm font-black uppercase tracking-wider text-red-900">Key takeaway</div>
                  <div className="mt-2 text-lg font-extrabold text-gray-900">
                    AI compresses your business into a brand description.
                  </div>
                  <div className="mt-2 text-base font-bold text-gray-700">
                    Recommendation systems require decision frameworks.
                  </div>
                </div>
              </div>
            </div>
            </LockedSection>
          </Section>
        </div>
      </div>

      {/* SECTION 3: RECOMMENDATION READINESS AUDIT (FORENSIC) */}
      <div className="w-full border-b-2 border-gray-300 bg-gray-50">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <Section id="section_3" title="03. RECOMMENDATION READINESS AUDIT">
            <div className="mb-10 flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-4 border-red-600 bg-red-600 text-2xl font-black text-white">
                03
              </div>
              <div>
                <div className="text-3xl font-extrabold tracking-tight text-gray-900">
                  Recommendation Readiness Audit
                </div>
                <div className="mt-2 text-base font-bold text-gray-700">
                  Decision-level gaps preventing AI recommendations
                </div>
              </div>
            </div>

            {/* OPPORTUNITY TEASER */}
            {isDetailLocked && (
              <div className="mb-6 rounded-xl border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50 p-4">
                <div className="text-sm font-bold text-gray-900">
                  💡 {decisionAudit?.filter(e => e?.status === 'missing' || e?.status === 'weak').length || 'Multiple'} decision elements are blocking AI recommendations right now
                </div>
                <div className="mt-2 text-xs text-gray-700 font-medium">
                  Each one is a specific opportunity to turn browsers into buyers through AI answers.
                </div>
              </div>
            )}

            <LockedSection locked={lockedSections.has('section_3_details')} onUnlock={onUnlock}>
            {/* CRITICAL DECISION ELEMENTS - FORENSIC AUDIT CARDS */}
            <div className="mb-10">
              <div className="mb-6 text-sm font-black uppercase tracking-wider text-gray-800">
                Critical Decision Elements Missing
              </div>
              
              <div className="grid gap-5 md:grid-cols-2">
                {(decisionAudit || []).map((elem, i) => {
                  const statusIcon = elem?.status === 'missing' ? '❌' : elem?.status === 'weak' ? '⚠️' : elem?.status === 'fragmented' ? '🟡' : '✅'
                  const statusColor = elem?.status === 'missing' ? 'red' : elem?.status === 'weak' ? 'orange' : elem?.status === 'fragmented' ? 'yellow' : 'green'
                  const borderClass = elem?.status === 'missing' || elem?.status === 'weak' ? 'border-gray-400' : 'border-gray-300'
                  const bgClass = elem?.status === 'missing' ? 'bg-red-50' : elem?.status === 'weak' ? 'bg-orange-50' : 'bg-white'
                  
                  const ev = resolveEvidence(elem?.evidence_refs)
                  
                  return (
                    <div
                      key={i}
                      className={`rounded-xl border-2 ${borderClass} ${bgClass} p-6 shadow-sm`}
                    >
                      {/* Element header */}
                      <div className="mb-4 flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="text-lg font-black text-gray-900">
                            {safeText(elem?.element_name, 'Decision Element')}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{statusIcon}</span>
                          <span className={`text-xs font-bold uppercase tracking-wider ${statusColor === 'red' ? 'text-red-700' : statusColor === 'orange' ? 'text-orange-700' : 'text-gray-600'}`}>
                            {safeText(elem?.status, 'unknown')}
                          </span>
                        </div>
                      </div>

                      {/* What AI expects */}
                      <div className="mb-3 rounded-lg border border-gray-300 bg-white p-3">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                          What AI expects
                        </div>
                        <div className="mt-1 text-sm font-semibold text-gray-800">
                          {safeText(elem?.ai_expectation, 'LLMs require structured, quotable content.')}
                        </div>
                      </div>

                      {/* What we found */}
                      <div className="mb-3">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                          What we found
                        </div>
                        <div className="mt-1 text-sm font-bold text-gray-900">
                          {safeText(elem?.what_found, 'Not detected on analyzed pages.')}
                        </div>
                      </div>

                      {/* Recommendation impact */}
                      <div className="rounded-lg border-l-4 border-gray-800 bg-gray-100 p-3">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-gray-700">
                          Impact on recommendations
                        </div>
                        <div className="mt-1 text-sm font-bold text-gray-900">
                          {safeText(elem?.recommendation_impact, 'AI cannot confidently recommend without this.')}
                        </div>
                      </div>

                      {/* Evidence */}
                      {ev.length > 0 && (
                        <details className="mt-3">
                          <summary className="cursor-pointer text-xs font-semibold text-gray-500 hover:text-gray-700">
                            Evidence ({ev.length})
                          </summary>
                          <div className="mt-2 space-y-1 text-[10px] text-gray-600">
                            {ev.map((e, idx) => (
                              <div key={idx}>
                                {safeText(Array.isArray(e?.source_urls) ? e.source_urls[0] : null, meta.domain || 'source')}
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* DECISION COVERAGE SCORE */}
            <div className="mb-10 rounded-xl border-2 border-gray-400 bg-white p-8 shadow-md">
              <div className="mb-5 text-sm font-black uppercase tracking-wider text-gray-800">
                Decision Coverage Score
              </div>
              
              {!decisionScore || (decisionScore.total === 0) ? (
                // UNAVAILABLE STATE
                <div className="text-center">
                  <div className="mb-4 text-4xl">⚠️</div>
                  <div className="mb-2 text-lg font-bold text-gray-900">Score Unavailable</div>
                  <div className="text-sm text-gray-600">
                    Audit output missing decision coverage data.
                  </div>
                  <div className="mt-4 grid gap-4 md:grid-cols-3">
                    <div className="text-center">
                      <div className="text-3xl font-black text-gray-400">—</div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-wider text-gray-500">
                        ✔️ Present
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-black text-gray-400">—</div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-wider text-gray-500">
                        ⚠️ Weak
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-black text-gray-400">—</div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-wider text-gray-500">
                        ❌ Missing
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                // NORMAL STATE (data exists)
                <>
                  <div className="grid gap-6 md:grid-cols-3">
                    <div className="text-center">
                      <div className="text-5xl font-black text-green-600">
                        {decisionScore.present}
                      </div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-wider text-gray-600">
                        ✔️ Present
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-5xl font-black text-orange-600">
                        {decisionScore.weak}
                      </div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-wider text-gray-600">
                        ⚠️ Weak
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-5xl font-black text-red-600">
                        {decisionScore.missing}
                      </div>
                      <div className="mt-2 text-xs font-bold uppercase tracking-wider text-gray-600">
                        ❌ Missing
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 border-t border-gray-300 pt-6 text-center">
                    <div className="text-xs font-bold uppercase tracking-wider text-gray-500">
                      Total Elements Analyzed
                    </div>
                    <div className="mt-2 text-3xl font-black text-gray-900">
                      {decisionScore.total}
                    </div>
                    <div className="mt-3 text-sm font-bold text-gray-800">
                      AI recommendation systems require near-complete decision coverage.
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* VERDICT - STRENGTHENED */}
            <div className="rounded-xl border-4 border-red-700 bg-red-50 p-8 shadow-lg">
              <div className="flex items-start gap-4">
                <div className="text-5xl">🔴</div>
                <div>
                  <div className="text-sm font-black uppercase tracking-wider text-red-900">
                    Verdict: Recommendation Blocked
                  </div>
                  <div className="mt-3 text-xl font-extrabold text-gray-900">
                    AI lacks sufficient decision-level data to <span className="text-red-700">safely recommend</span> this business <span className="text-red-700">over competitors</span>.
                  </div>
                </div>
              </div>
            </div>
            </LockedSection>
          </Section>
        </div>
      </div>

      {/* SECTION 4: WHAT AI SYSTEMS NEED (GRANULAR BREAKDOWN) */}
      <div className="w-full border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-12">
          <Section id="section_4" title="04. WHAT AI SYSTEMS NEED TO RECOMMEND A BUSINESS">
            <div className="mb-8 flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-gray-800 bg-gray-800 text-2xl font-black text-white">
                04
              </div>
              <div>
                <div className="text-3xl font-extrabold tracking-tight text-gray-900">
                  What AI systems need to recommend a business
                </div>
                <div className="mt-2 text-base font-bold text-gray-700">
                  AI decision-layer requirements (before / after)
                </div>
              </div>
            </div>

            {/* OPPORTUNITY TEASER */}
            {isDetailLocked && (
              <div className="mb-6 rounded-xl border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50 p-4">
                <div className="text-sm font-bold text-gray-900">
                  💡 {aiRequirements?.length || 'Multiple'} specific improvements will turn your site into an AI-recommended solution
                </div>
                <div className="mt-2 text-xs text-gray-700 font-medium">
                  See the complete before/after transformation and exactly what to build.
                </div>
              </div>
            )}

            <LockedSection locked={lockedSections.has('section_4')} onUnlock={onUnlock}>
            {aiRequirements.length === 0 ? (
              <div className="rounded-xl border-2 border-gray-300 bg-gray-50 p-8 text-center">
                <div className="text-lg font-bold text-gray-900">AI Requirements Unavailable</div>
                <div className="mt-2 text-sm text-gray-600">
                  Requirements data not yet generated. Run new audit to populate this section.
                </div>
              </div>
            ) : (
              <div className="space-y-8">
                {/* BEFORE/AFTER columns layout */}
                <div className="grid gap-8 md:grid-cols-2">
                  {/* LEFT: BEFORE (Problems) */}
                  <div className="rounded-2xl border-2 border-red-600 bg-red-50 p-6">
                    <div className="mb-5">
                      <div className="text-sm font-black uppercase tracking-wider text-red-900">
                        ❌ BEFORE (Current State)
                      </div>
                      <div className="mt-1 text-xs font-semibold text-red-700">
                        What is missing / weak right now
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      {aiRequirementsBefore.length > 0 ? (
                        aiRequirementsBefore.map((req, i) => {
                          const statusIcon = req?.current_status === 'not_found' ? '❌' : '⚠️'
                          return (
                            <div key={i} className="rounded-lg border-2 border-red-300 bg-white p-4">
                              <div className="mb-2 flex items-start justify-between gap-2">
                                <div className="flex-1 text-sm font-black text-gray-900">
                                  {safeText(req?.requirement_name, 'AI Requirement')}
                                </div>
                                <span className="text-lg">{statusIcon}</span>
                              </div>
                              
                              <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-gray-500">
                                Why AI needs this
                              </div>
                              <div className="mb-3 text-xs font-semibold text-gray-700">
                                {safeText(req?.why_ai_needs_this, 'AI systems need this.')}
                              </div>
                              
                              <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-red-700">
                                Impact if missing
                              </div>
                              <div className="text-xs font-bold text-gray-900">
                                {safeText(req?.impact_if_missing, 'Affects recommendations.')}
                              </div>
                            </div>
                          )
                        })
                      ) : (
                        <div className="text-sm text-gray-600">No before-state requirements detected</div>
                      )}
                    </div>
                  </div>
                  
                  {/* RIGHT: AFTER (Solutions) */}
                  <div className="rounded-2xl border-2 border-green-600 bg-green-50 p-6">
                    <div className="mb-5">
                      <div className="text-sm font-black uppercase tracking-wider text-green-900">
                        ✅ AFTER (What Must Be Built)
                      </div>
                      <div className="mt-1 text-xs font-semibold text-green-700">
                        What needs to exist for AI recommendations
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      {aiRequirementsAfter.length > 0 ? (
                        aiRequirementsAfter.map((req, i) => (
                          <div key={i} className="rounded-lg border-2 border-green-300 bg-white p-4">
                            <div className="mb-2 text-sm font-black text-gray-900">
                              {safeText(req?.requirement_name, 'AI Requirement')}
                            </div>
                            
                            <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-gray-500">
                              What must be built
                            </div>
                            <div className="mb-3 text-xs font-semibold text-gray-700">
                              {safeText(req?.what_must_be_built, 'Build structured content.')}
                            </div>
                            
                            <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-green-700">
                              AI outcome unlocked
                            </div>
                            <div className="text-xs font-bold text-gray-900">
                              {safeText(req?.ai_outcome_unlocked, 'AI can recommend with confidence.')}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-sm text-gray-600">No after-state requirements detected</div>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Legacy category-based rendering (fallback for old ai_requirements format) */}
                {aiRequirementsLegacy.length > 0 && aiRequirementsBefore.length === 0 && (
                  <div className="space-y-6">
                    {Object.entries(requirementsByCategory).map(([category, reqs]) => {
                      if (!reqs || reqs.length === 0) return null
                      
                      const categoryLabel = categoryLabels[category] || category
                      const problemCount = reqs.filter(r => r?.current_status === 'missing' || r?.current_status === 'weak').length
                      
                      return (
                        <div key={category} className="rounded-2xl border-2 border-gray-300 bg-gray-50 p-6">
                          <div className="mb-5 flex items-center justify-between">
                            <div>
                              <div className="text-sm font-black uppercase tracking-wider text-gray-900">
                                {categoryLabel}
                              </div>
                              <div className="mt-1 text-xs font-semibold text-gray-600">
                                {problemCount} / {reqs.length} issues detected
                              </div>
                            </div>
                            <div className="rounded-full bg-red-600 px-3 py-1 text-xs font-black text-white">
                              {problemCount} PROBLEMS
                            </div>
                          </div>

                          <div className="grid gap-4 md:grid-cols-2">
                            {reqs.map((req, i) => {
                              const statusIcon = req?.current_status === 'missing' ? '❌' : req?.current_status === 'weak' ? '⚠️' : '✅'
                              const borderClass = req?.current_status === 'missing' || req?.current_status === 'weak' ? 'border-gray-400' : 'border-green-600'
                              
                              return (
                                <div key={i} className={`rounded-xl border-2 ${borderClass} bg-white p-4`}>
                                  <div className="mb-3 flex items-start justify-between gap-2">
                                    <div className="flex-1 text-sm font-black text-gray-900">
                                      {safeText(req?.requirement_name, 'AI Requirement')}
                                    </div>
                                    <span className="text-xl">{statusIcon}</span>
                                  </div>

                                  <div className="mb-3 rounded-lg border-l-4 border-red-600 bg-red-50 p-3">
                                    <div className="text-[10px] font-bold uppercase tracking-wider text-red-900">
                                      ❌ Before (Current)
                                    </div>
                                    <div className="mt-1 text-xs font-semibold text-gray-800">
                                      {safeText(req?.problem_statement, 'Not detected.')}
                                    </div>
                                  </div>

                                  <div className="mb-3 rounded-lg border-l-4 border-green-600 bg-green-50 p-3">
                                    <div className="text-[10px] font-bold uppercase tracking-wider text-green-900">
                                      ✅ After (Needed)
                                    </div>
                                    <div className="mt-1 text-xs font-semibold text-gray-800">
                                      {safeText(req?.solution_statement, 'AI needs structured content.')}
                                    </div>
                                  </div>

                                  <div className="text-xs font-bold text-gray-600">
                                    <span className="text-gray-500">Impact:</span> {safeText(req?.ai_impact, 'Affects recommendations.')}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {aiRequirements.length > 0 && (
              <div className="mt-8 rounded-xl border-2 border-gray-400 bg-white p-6">
                <div className="mb-4 text-sm font-black uppercase tracking-wider text-gray-800">
                  AI Requirements Summary
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="text-center">
                    <div className="text-4xl font-black text-red-600">
                      {aiRequirementsBefore.filter(r => r?.current_status === 'not_found').length || aiRequirementsLegacy.filter(r => r?.current_status === 'missing').length}
                    </div>
                    <div className="mt-2 text-xs font-bold uppercase text-gray-600">❌ Missing</div>
                  </div>
                  <div className="text-center">
                    <div className="text-4xl font-black text-orange-600">
                      {aiRequirementsBefore.filter(r => r?.current_status === 'weak').length || aiRequirementsLegacy.filter(r => r?.current_status === 'weak').length}
                    </div>
                    <div className="mt-2 text-xs font-bold uppercase text-gray-600">⚠️ Weak</div>
                  </div>
                  <div className="text-center">
                    <div className="text-4xl font-black text-green-600">
                      {aiRequirementsLegacy.filter(r => r?.current_status === 'present').length}
                    </div>
                    <div className="mt-2 text-xs font-bold uppercase text-gray-600">✅ Present</div>
                  </div>
                </div>
                <div className="mt-4 border-t border-gray-300 pt-4 text-center text-sm font-bold text-gray-800">
                  AI systems require near-complete coverage across all categories.
                </div>
              </div>
            )}
            </LockedSection>
          </Section>
        </div>
      </div>

      {/* SECTION 5: COST OF DOING NOTHING */}
      <div className="w-full bg-gray-900">
        <div className="mx-auto max-w-6xl px-4 py-14 text-white">
          <Section id="section_5" title="05. COST OF DOING NOTHING">
            <div className="mb-6 flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-red-600 bg-red-600 text-2xl font-black text-white">
                05
              </div>
              <div className="text-3xl font-extrabold tracking-tight text-white">Every month you wait, competitors get stronger</div>
            </div>
            <LockedSection locked={lockedSections.has('section_5')} onUnlock={onUnlock}>
              
              {/* STRAŠÁK 1: Konkurence utíká */}
              <div className="mt-6 rounded-xl border-2 border-red-500 bg-gradient-to-br from-red-950 to-red-900 p-8 shadow-2xl">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-red-500 text-xl font-black text-white">
                    01
                  </div>
                  <div>
                    <h3 className="text-2xl font-black text-red-100 mb-3">Your competitors are already being recommended</h3>
                    <p className="text-lg font-semibold text-red-200 leading-relaxed">
                      Every day AI recommends them instead of you. That's traffic you'll never get back. 
                      <span className="block mt-2 text-red-300">
                        ChatGPT, Claude, Gemini — they're answering thousands of buyer questions right now. Without mentioning you.
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              {/* STRAŠÁK 2: Traffic compounds */}
              <div className="mt-6 rounded-xl border-2 border-orange-500 bg-gradient-to-br from-orange-950 to-orange-900 p-8 shadow-2xl">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-orange-500 text-xl font-black text-white">
                    02
                  </div>
                  <div>
                    <h3 className="text-2xl font-black text-orange-100 mb-3">This traffic grows exponentially — without you</h3>
                    <p className="text-lg font-semibold text-orange-200 leading-relaxed">
                      AI-driven search traffic is doubling every 6 months. The companies that get recommended NOW will dominate recommendations LATER.
                      <span className="block mt-2 text-orange-300">
                        First movers win. Late movers fight for scraps.
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              {/* STRAŠÁK 3: Window closing */}
              <div className="mt-6 rounded-xl border-2 border-yellow-500 bg-gradient-to-br from-yellow-950 to-yellow-900 p-8 shadow-2xl">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-yellow-500 text-xl font-black text-gray-900">
                    03
                  </div>
                  <div>
                    <h3 className="text-2xl font-black text-yellow-100 mb-3">The window is closing — fast</h3>
                    <p className="text-lg font-semibold text-yellow-200 leading-relaxed">
                      AI models learn from early winners. The longer your competitors are recommended, the harder it is to overtake them.
                      <span className="block mt-2 text-yellow-300">
                        Waiting 6 months = 6 months of lost traffic + reinforced competitor advantage.
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              {/* CTA BUTTON — přechod k řešení */}
              <div className="mt-10 flex justify-center">
                <a 
                  href="#section_6" 
                  className="group relative inline-flex items-center gap-4 rounded-2xl border-2 border-emerald-500 bg-gradient-to-r from-emerald-600 to-emerald-500 px-12 py-6 shadow-2xl transition-all hover:scale-105 hover:shadow-emerald-500/50"
                >
                  <div className="text-center">
                    <div className="text-2xl font-black text-white mb-1">
                      Show me the solution
                    </div>
                    <div className="text-sm font-semibold text-emerald-100">
                      See your monthly growth plan below
                    </div>
                  </div>
                  <svg className="w-8 h-8 text-white group-hover:translate-y-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                </a>
              </div>

            </LockedSection>
          </Section>
        </div>
      </div>

      {/* SECTION 6: COMPLETE AI-READY WEBSITE — THE SOLUTION */}
      {/* Only render if Section 6 data exists (backend controls this) */}
      {normalized?.section_6 && (
      <div className="w-full border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <Section id="section_6" title="06. YOUR GROWTH PLAN">
            <div className="mb-8 flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-emerald-600 bg-emerald-600 text-2xl font-black text-white">
                06
              </div>
              <div className="text-3xl font-extrabold tracking-tight text-gray-900">Your growth plan</div>
            </div>
            {lockedSections.has('section_6') ? (
              <LockOverlay onUnlock={onUnlock} />
            ) : (
              (() => {
                const missingCount = decisionAudit.filter(e => e?.status === 'missing').length
                const weakCount = decisionAudit.filter(e => e?.status === 'weak').length
                const totalGaps = missingCount + weakCount
                
                return (
                  <div className="space-y-12">
                    
                    {/* HERO — AI-FOCUSED HEADLINE */}
                    <div className="text-center space-y-6">
                      <h2 className="text-5xl md:text-6xl font-black text-gray-900 leading-tight">
                        <span className="bg-gradient-to-r from-emerald-600 to-emerald-500 bg-clip-text text-transparent">Grow your traffic</span><br className="hidden md:block" />
                        <span className="text-gray-900">every single month</span>
                      </h2>
                      <p className="mx-auto max-w-3xl text-xl font-semibold text-gray-700 leading-relaxed">
                        AI-optimized pages that get you recommended in ChatGPT, Claude, Gemini, Perplexity — plus Google, Bing & traditional search.
                      </p>
                    </div>

                    {/* WHAT WE DO — VÝRAZNÉ VYSVĚTLENÍ */}
                    <div className="rounded-2xl border-4 border-emerald-600 bg-gradient-to-br from-white to-emerald-50 p-10 shadow-2xl">
                      <div className="text-center space-y-6">
                        <div className="inline-block rounded-full bg-emerald-600 px-6 py-2">
                          <span className="text-sm font-black uppercase tracking-wider text-white">What you get every month</span>
                        </div>
                        
                        <h3 className="text-4xl font-black text-gray-900 leading-tight">
                          Custom pages for your website<br className="hidden md:block" />
                          that get you <span className="text-emerald-600">free traffic</span> from<br className="hidden md:block" />
                          ChatGPT, Claude, Gemini — and Google search
                        </h3>
                        
                        <div className="mx-auto max-w-4xl space-y-4">
                          <p className="text-xl font-bold text-gray-800 leading-relaxed">
                            Every page is written specifically for your business, product, or service — and optimized to appear in:
                          </p>
                          
                          <div className="grid gap-4 md:grid-cols-2 text-left mt-6">
                            <div className="flex items-start gap-3 rounded-xl border-2 border-emerald-500 bg-white p-5">
                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-sm font-black text-white">
                                01
                              </div>
                              <div>
                                <div className="font-black text-gray-900">AI model recommendations</div>
                                <div className="text-sm font-semibold text-gray-600">ChatGPT, Claude, Gemini, Perplexity suggest you to buyers</div>
                              </div>
                            </div>
                            <div className="flex items-start gap-3 rounded-xl border-2 border-emerald-500 bg-white p-5">
                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-sm font-black text-white">
                                02
                              </div>
                              <div>
                                <div className="font-black text-gray-900">Traditional search results</div>
                                <div className="text-sm font-semibold text-gray-600">Google, Bing, Yahoo rank you for buyer keywords</div>
                              </div>
                            </div>
                            <div className="flex items-start gap-3 rounded-xl border-2 border-emerald-500 bg-white p-5">
                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-sm font-black text-white">
                                03
                              </div>
                              <div>
                                <div className="font-black text-gray-900">100% personalized to your business</div>
                                <div className="text-sm font-semibold text-gray-600">Written for your specific services, products, and customers</div>
                              </div>
                            </div>
                            <div className="flex items-start gap-3 rounded-xl border-2 border-emerald-500 bg-white p-5">
                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-sm font-black text-white">
                                04
                              </div>
                              <div>
                                <div className="font-black text-gray-900">Human-written, expert content</div>
                                <div className="text-sm font-semibold text-gray-600">Not generic AI text — real content for your niche</div>
                              </div>
                            </div>
                          </div>

                          <div className="mt-6 rounded-xl border-2 border-gray-900 bg-gray-900 p-6">
                            <p className="text-lg font-black text-white">
                              Every page is ready to publish and starts driving qualified traffic from day one
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* WHY AI-OPTIMIZED PAGES WORK */}
                    <div className="rounded-2xl border-2 border-gray-300 bg-gray-50 p-8">
                      <div className="mb-6 text-center space-y-2">
                        <div className="text-sm font-black uppercase tracking-wider text-gray-600">
                          Why this is the future of customer acquisition
                        </div>
                        <div className="text-xl font-bold text-gray-900">
                          AI-driven traffic converts better than any other channel
                        </div>
                      </div>
                      <div className="mx-auto max-w-3xl space-y-4">
                        <div className="flex items-start gap-4 rounded-lg bg-white p-5 border-2 border-emerald-200">
                          <span className="text-3xl">🚀</span>
                          <div>
                            <div className="font-black text-gray-900 text-lg">High-intent, ready-to-buy traffic</div>
                            <div className="text-sm text-gray-700 font-medium mt-1">
                              Users asking AI for recommendations are actively comparing solutions — they're not browsing, they're deciding
                            </div>
                          </div>
                        </div>
                        <div className="flex items-start gap-4 rounded-lg bg-white p-5 border-2 border-gray-200">
                          <span className="text-3xl">🎯</span>
                          <div>
                            <div className="font-black text-gray-900 text-lg">Each page = another chance to be recommended</div>
                            <div className="text-sm text-gray-700 font-medium mt-1">
                              More AI-ready pages = more queries you rank for = more customers discovering you
                            </div>
                          </div>
                        </div>
                        <div className="flex items-start gap-4 rounded-lg bg-white p-5 border-2 border-gray-200">
                          <span className="text-3xl">⚡</span>
                          <div>
                            <div className="font-black text-gray-900 text-lg">Compounding growth across all channels</div>
                            <div className="text-sm text-gray-700 font-medium mt-1">
                              As you add pages, your authority grows — AI models trust you more, recommend you more often
                            </div>
                          </div>
                        </div>
                        <div className="flex items-start gap-4 rounded-lg bg-emerald-50 p-5 border-2 border-emerald-500">
                          <span className="text-3xl">💰</span>
                          <div>
                            <div className="font-black text-emerald-900 text-lg">Zero ad spend — 100% owned traffic</div>
                            <div className="text-sm text-emerald-800 font-semibold mt-1">
                              Unlike paid ads that stop when you stop paying, this traffic is yours permanently
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* PRICING — AI GROWTH SPEED */}
                    <div>
                      <div className="text-center space-y-6 mb-16">
                        <div className="mb-3 text-sm font-black uppercase tracking-wider text-gray-600">
                          Choose your AI visibility growth
                        </div>
                        <h3 className="text-3xl font-black text-gray-900">
                          How fast do you want to grow in AI channels?
                        </h3>
                        
                        {/* MONTHLY/YEARLY TOGGLE */}
                        <div className="flex items-center justify-center gap-4 mb-10">
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

                      <div className="grid gap-6 lg:grid-cols-3">
                        
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

                          <button className="w-full rounded-xl border-2 border-gray-300 bg-white py-4 text-base font-bold text-gray-900 hover:bg-gray-50 transition-all">
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

                          <button className="w-full rounded-xl bg-emerald-600 py-4 text-base font-bold text-white hover:bg-emerald-700 transition-all shadow-lg">
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

                          <button className="w-full rounded-xl border-2 border-gray-300 bg-white py-4 text-base font-bold text-gray-900 hover:bg-gray-50 transition-all">
                            {PRICING_PLANS.scale.ctaLabel}
                          </button>
                        </div>
                      </div>

                      {/* BOTTOM VALUE STATEMENT — AI FOCUS */}
                      <div className="mt-12 rounded-xl border-2 border-emerald-500 bg-gradient-to-r from-emerald-50 to-white p-8 text-center shadow-lg">
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

                  </div>
                )
              })()
            )}
          </Section>
        </div>
      </div>
      )}

      {/* Sticky mobile CTA - only show in locked state */}
      {isLocked && (
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t-2 border-blue-200 bg-gradient-to-r from-blue-600/95 to-purple-600/95 p-3 backdrop-blur md:hidden">
        <button
          onClick={onUnlock}
          className="w-full rounded-lg bg-white px-4 py-3 text-sm font-bold text-gray-900 hover:bg-gray-50 shadow-lg"
        >
          Get Your AI Traffic Action Plan
        </button>
      </div>
      )}

      {/* Email gate for anonymous users */}
      {showEmailGate && isPreview && (
        <EmailGate 
          auditId={jobId} 
          onSuccess={() => {
            setShowEmailGate(false)
            refetch() // Refresh to get locked state
          }} 
        />
      )}

      {/* Pricing modal for registered users */}
      {showUnlockModal && (
        <UnlockModal 
          auditId={jobId}
          onClose={() => setShowUnlockModal(false)}
        />
      )}
    </div>
  )
}


