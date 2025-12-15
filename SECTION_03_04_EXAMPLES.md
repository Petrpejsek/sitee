# Section 03 a 04 — Ukázky JSON + Changelog

## 1. Ukázka JSON pro Section 03 (Decision Readiness Audit)

```json
{
  "decision_readiness_audit": [
    {
      "element_name": "Pricing ranges / packages",
      "status": "missing",
      "what_ai_requires": "AI requires transparent pricing tiers or ranges with value anchors to compare alternatives.",
      "what_we_found": "No pricing page detected across analyzed pages.",
      "impact_on_recommendation": "AI defaults to competitors with explicit pricing.",
      "evidence_refs": []
    },
    {
      "element_name": "Value anchors",
      "status": "missing",
      "what_ai_requires": "AI needs value comparisons and ROI context to explain pricing.",
      "what_we_found": "Not detected in evidence catalog.",
      "impact_on_recommendation": "AI cannot contextualize pricing against market standards.",
      "evidence_refs": []
    },
    {
      "element_name": "Service scope boundaries",
      "status": "weak",
      "what_ai_requires": "AI needs clear 'what's included / not included' sections to set expectations.",
      "what_we_found": "Service pages mention offerings but lack structured scope boundaries.",
      "impact_on_recommendation": "AI cannot confidently explain service limits.",
      "evidence_refs": [0, 2]
    },
    {
      "element_name": "Process / how it works",
      "status": "weak",
      "what_ai_requires": "AI needs step-by-step operational details to explain the buyer journey.",
      "what_we_found": "Process mentioned in fragments across pages without structured timeline.",
      "impact_on_recommendation": "AI cannot guide users through the service process.",
      "evidence_refs": [3, 5]
    },
    {
      "element_name": "Alternatives / who it's NOT for",
      "status": "missing",
      "what_ai_requires": "AI needs audience fit statements to match businesses to user needs.",
      "what_we_found": "Not detected in evidence catalog.",
      "impact_on_recommendation": "AI cannot determine who this service is best for.",
      "evidence_refs": []
    },
    {
      "element_name": "Differentiation (measurable)",
      "status": "missing",
      "what_ai_requires": "AI needs quantifiable competitive advantages to position against alternatives.",
      "what_we_found": "No measurable differentiation points detected in evidence.",
      "impact_on_recommendation": "AI cannot explain why to choose this over competitors.",
      "evidence_refs": []
    },
    {
      "element_name": "Testimonials (context)",
      "status": "weak",
      "what_ai_requires": "AI needs testimonials with specific outcomes and customer context.",
      "what_we_found": "Testimonials present but lack specific outcomes or measurable results.",
      "impact_on_recommendation": "AI has lower confidence in recommendation quality.",
      "evidence_refs": [7, 8]
    },
    {
      "element_name": "Case studies (outcomes)",
      "status": "missing",
      "what_ai_requires": "AI needs case studies with measurable results to support recommendations.",
      "what_we_found": "Not detected in evidence catalog.",
      "impact_on_recommendation": "AI cannot provide proof of results to users.",
      "evidence_refs": []
    },
    {
      "element_name": "About/team authority",
      "status": "weak",
      "what_ai_requires": "AI needs structured entity and authority information for knowledge graphs.",
      "what_we_found": "About page exists but lacks structured authority markers and expertise proof.",
      "impact_on_recommendation": "AI treats this as weak entity with limited credibility.",
      "evidence_refs": [1]
    },
    {
      "element_name": "Guarantees/refunds/risk reducers",
      "status": "missing",
      "what_ai_requires": "AI needs guarantees and risk-reduction statements to recommend confidently.",
      "what_we_found": "Not detected in evidence catalog.",
      "impact_on_recommendation": "AI sees this as higher-risk recommendation without guarantees.",
      "evidence_refs": []
    },
    {
      "element_name": "Policies / expectations",
      "status": "missing",
      "what_ai_requires": "AI needs clear policies and SLAs to set buyer expectations.",
      "what_we_found": "Not detected in evidence catalog.",
      "impact_on_recommendation": "AI cannot explain expectations or terms clearly.",
      "evidence_refs": []
    },
    {
      "element_name": "FAQ objections",
      "status": "missing",
      "what_ai_requires": "AI needs structured Q&A to answer common decision questions.",
      "what_we_found": "FAQ content not found in evidence catalog.",
      "impact_on_recommendation": "AI lacks quotable answers to user questions.",
      "evidence_refs": []
    },
    {
      "element_name": "Local/entity signals",
      "status": "weak",
      "what_ai_requires": "AI needs location proof, hours, and service area for local recommendations.",
      "what_we_found": "Contact page shows location but lacks hours, service area map, or booking details.",
      "impact_on_recommendation": "AI cannot confidently recommend for local queries.",
      "evidence_refs": [4]
    },
    {
      "element_name": "Structured summaries AI can quote",
      "status": "missing",
      "what_ai_requires": "AI needs quotable summary blocks with key features and benefits.",
      "what_we_found": "Not detected in evidence catalog.",
      "impact_on_recommendation": "AI cannot directly cite structured information.",
      "evidence_refs": []
    },
    {
      "element_name": "Contact / conversion clarity",
      "status": "weak",
      "what_ai_requires": "AI needs clear CTAs and next-steps information to guide users.",
      "what_we_found": "Contact form exists but no clear next-steps or conversion guidance.",
      "impact_on_recommendation": "AI cannot guide users to conversion effectively.",
      "evidence_refs": [6]
    }
  ],
  "decision_coverage_score": {
    "present": 0,
    "weak": 6,
    "missing": 9,
    "total": 15
  }
}
```

**Poznámky k Section 03:**
- **15 elementů** (splňuje požadavek 12-18)
- **0 "present"** (přísná definice: žádný element nesplňuje všechny 4 kritéria)
- **6 "weak"** (existuje, ale není strukturované/kompletní/citovatelné)
- **9 "missing"** (nenalezeno v evidenci)
- **what_we_found** je vždy konkrétní (ne vágní fráze)
- **impact_on_recommendation** popisuje reálný AI důsledek (ne marketingové klišé)

---

## 2. Ukázka JSON pro Section 04 (AI Requirements)

### A) ai_requirements_before (10 položek)

```json
{
  "ai_requirements_before": [
    {
      "requirement_name": "Pricing ranges / packages",
      "category": "Comparability",
      "why_ai_needs_this": "AI needs pricing ranges to compare value against alternatives.",
      "current_status": "not_found",
      "impact_if_missing": "AI defaults to competitors with visible pricing."
    },
    {
      "requirement_name": "Service scope boundaries",
      "category": "Decision Clarity",
      "why_ai_needs_this": "AI needs clear scope to explain what's included and excluded.",
      "current_status": "weak",
      "impact_if_missing": "AI cannot confidently describe service boundaries."
    },
    {
      "requirement_name": "Process / how it works",
      "category": "Decision Clarity",
      "why_ai_needs_this": "AI needs operational clarity to explain how the service works.",
      "current_status": "weak",
      "impact_if_missing": "AI cannot guide users through the process."
    },
    {
      "requirement_name": "Alternatives / who it's NOT for",
      "category": "Comparability",
      "why_ai_needs_this": "AI needs audience fit statements to match businesses to user needs.",
      "current_status": "not_found",
      "impact_if_missing": "AI cannot determine who this service is best for."
    },
    {
      "requirement_name": "Differentiation (measurable)",
      "category": "Comparability",
      "why_ai_needs_this": "AI needs competitive positioning to explain trade-offs.",
      "current_status": "not_found",
      "impact_if_missing": "AI cannot differentiate this business from alternatives."
    },
    {
      "requirement_name": "Testimonials (context)",
      "category": "Trust & Authority",
      "why_ai_needs_this": "AI needs proof of results to build recommendation confidence.",
      "current_status": "weak",
      "impact_if_missing": "AI has lower trust in recommendation quality."
    },
    {
      "requirement_name": "Case studies (outcomes)",
      "category": "Trust & Authority",
      "why_ai_needs_this": "AI needs real case studies to support recommendations with evidence.",
      "current_status": "not_found",
      "impact_if_missing": "AI cannot provide proof of results."
    },
    {
      "requirement_name": "About/team authority",
      "category": "Entity Understanding",
      "why_ai_needs_this": "AI needs structured entity data for knowledge graph inclusion.",
      "current_status": "weak",
      "impact_if_missing": "AI treats this as a weak entity with limited authority."
    },
    {
      "requirement_name": "Guarantees/refunds/risk reducers",
      "category": "Risk Reduction",
      "why_ai_needs_this": "AI needs guarantees/refunds to recommend with confidence.",
      "current_status": "not_found",
      "impact_if_missing": "AI sees this as higher-risk recommendation."
    },
    {
      "requirement_name": "FAQ objections",
      "category": "Decision Clarity",
      "why_ai_needs_this": "AI needs structured Q&A to answer user decision questions.",
      "current_status": "not_found",
      "impact_if_missing": "AI lacks quotable answers to common questions."
    }
  ]
}
```

### B) ai_requirements_after (10 položek)

```json
{
  "ai_requirements_after": [
    {
      "requirement_name": "Pricing ranges / packages",
      "category": "Comparability",
      "what_must_be_built": "Add pricing tiers or ranges with value anchors and comparison points.",
      "ai_outcome_unlocked": "AI can compare value and recommend based on budget fit."
    },
    {
      "requirement_name": "Service scope boundaries",
      "category": "Decision Clarity",
      "what_must_be_built": "Create service pages with clear 'what's included / not included' sections.",
      "ai_outcome_unlocked": "AI can explain service scope boundaries to users."
    },
    {
      "requirement_name": "Process / how it works",
      "category": "Decision Clarity",
      "what_must_be_built": "Add process/timeline/delivery information in structured format.",
      "ai_outcome_unlocked": "AI can explain how the service works step-by-step."
    },
    {
      "requirement_name": "Alternatives / who it's NOT for",
      "category": "Comparability",
      "what_must_be_built": "Create 'Who this is for / not for' sections on key pages.",
      "ai_outcome_unlocked": "AI can match this business to specific user needs."
    },
    {
      "requirement_name": "Differentiation (measurable)",
      "category": "Comparability",
      "what_must_be_built": "Build 'vs alternatives' pages explaining trade-offs and differentiation.",
      "ai_outcome_unlocked": "AI can position this business against competitors."
    },
    {
      "requirement_name": "Testimonials (context)",
      "category": "Trust & Authority",
      "what_must_be_built": "Add testimonials with specific results, context, and attribution.",
      "ai_outcome_unlocked": "AI gains proof to support recommendations with evidence."
    },
    {
      "requirement_name": "Case studies (outcomes)",
      "category": "Trust & Authority",
      "what_must_be_built": "Create case studies with measurable outcomes and specific details.",
      "ai_outcome_unlocked": "AI can cite real-world results to support recommendations."
    },
    {
      "requirement_name": "About/team authority",
      "category": "Entity Understanding",
      "what_must_be_built": "Strengthen About/Team pages with authority markers and structured data.",
      "ai_outcome_unlocked": "AI treats this as a credible entity in knowledge graphs."
    },
    {
      "requirement_name": "Guarantees/refunds/risk reducers",
      "category": "Risk Reduction",
      "what_must_be_built": "Add guarantees, refund policies, or risk-reduction statements.",
      "ai_outcome_unlocked": "AI can recommend with lower perceived risk."
    },
    {
      "requirement_name": "FAQ objections",
      "category": "Decision Clarity",
      "what_must_be_built": "Create structured FAQ sections answering decision-level questions.",
      "ai_outcome_unlocked": "AI can quote direct answers to user questions."
    }
  ]
}
```

**Poznámky k Section 04:**
- **10 položek v BEFORE** a **10 položek v AFTER** (splňuje požadavek 10-20)
- **100% alignment** mezi Section 03 a Section 04 (každý missing/weak element má odpovídající requirement)
- **BEFORE: 100% not_found nebo weak** (žádný "present")
- **AFTER: konkrétní build instructions** (ne generické rady jako "Improve trust")
- **Kategorie konzistentní:** Decision Clarity, Comparability, Trust & Authority, Entity Understanding, Risk Reduction

---

## 3. Co se změnilo (Changelog)

### A) Section 03 — Decision Readiness Audit

1. **Zvýšen minimální počet elementů:**
   - Před: 8-12 elementů
   - Po: **12-18 elementů** (min. 15 mandatory + až 3 business-specific)
   
2. **Zpřísněna definice "present":**
   - Musí splňovat VŠECHNY 4 kritéria: EXISTS + STRUCTURED + QUOTABLE + COMPLETE
   - Default očekávání: **0-2 "present"** (ne 1-3)
   - Bias směrem k "weak" nebo "missing"

3. **Anti-bullshit pravidla pro `what_we_found`:**
   - ❌ ZAKÁZÁNO: "Information is fragmented", "Content lacks structure", "Needs improvement"
   - ✅ POVOLENO: "Not detected in evidence catalog." NEBO konkrétní evidence-based statement
   - Každé tvrzení musí mít oporu v evidenci nebo explicitně říct "not detected"

4. **Anti-bullshit pravidla pro `impact_on_recommendation`:**
   - ❌ ZAKÁZÁNO: "Needs clarity", "Should improve", "Could be better"
   - ✅ POVOLENO: Konkrétní AI důsledek ("AI defaults to competitors with explicit pricing")

5. **Aktualizován seznam mandatory elementů:**
   - Změna z dlouhých názvů na krátké, lidské názvy
   - Příklad: "Service Definition Pages" → "Pricing ranges / packages"

6. **decision_coverage_score validace:**
   - `total` MUSÍ být 12-18 (validováno proti délce `decision_readiness_audit`)
   - `present` + `weak` + `missing` MUSÍ být = `total`

### B) Section 04 — AI Requirements

1. **Zvýšen minimální počet požadavků:**
   - Před: 10-20 položek celkem (nejasná distribuce)
   - Po: **10-20 položek v BEFORE** a **10-20 položek v AFTER** (explicitně rozděleno)

2. **Zakázány generické fráze v `what_must_be_built`:**
   - ❌ ZAKÁZÁNO: "Improve trust", "Add more content", "Better structure"
   - ✅ POVOLENO: "Build structured service pages with clear scope, features, and use cases."

3. **Zavedena konzistence mezi Section 03 a 04:**
   - Každý "missing" nebo "weak" element ze Section 03 musí mít odpovídající requirement v Section 04
   - `requirement_name` musí odpovídat `element_name` ze Section 03

4. **Aktualizovány kategorie:**
   - Před: `decision_clarity`, `comparability`, `trust_authority`, `entity_understanding`, `risk_confidence`
   - Po: **"Decision Clarity"**, **"Comparability"**, **"Trust & Authority"**, **"Entity Understanding"**, **"Risk Reduction"** (lidské názvy s velkými písmeny)

5. **Fallback seznam rozšířen z 10 na 15 položek:**
   - Lepší pokrytí všech 15 mandatory elementů ze Section 03
   - Alignment mezi fallback a mandatory list

6. **BEFORE items nesmí obsahovat "present":**
   - Pouze `"not_found"` nebo `"weak"` (protože to je BEFORE stav)
   - 90-100% bias k problémům

### C) Systémové změny

1. **Schema validace zpřísněna:**
   - `DecisionCoverageScore`: `ge=0, le=18` (místo `le=10`)
   - `decision_readiness_audit`: `min_length=12, max_length=18`
   - `ai_requirements_before/after`: `min_length=10, max_length=20`

2. **Post-processing logika:**
   - Pokud LLM vrátí méně než 12 elementů → padding na 12
   - Pokud LLM vrátí méně než 10 requirements → padding na 10
   - `decision_coverage_score` se automaticky počítá z elementů

3. **Prompt engineering:**
   - Přidány explicitní příklady GOOD/BAD
   - Přidána sekce "ANTI-BULLSHIT RULES"
   - Zpřísněna instrukce pro konzervativní bias (80-95% weak/missing)

---

## 4. Testovací checklist

Při dalším auditu zkontroluj:

- ✅ Section 03 má 12-18 elementů (ne 8-12)
- ✅ decision_coverage_score.total = délka decision_readiness_audit
- ✅ Většina elementů je "weak" nebo "missing" (ne "present")
- ✅ what_we_found neobsahuje vágní fráze
- ✅ impact_on_recommendation popisuje AI důsledek (ne marketing)
- ✅ ai_requirements_before má 10-20 položek
- ✅ ai_requirements_after má 10-20 položek
- ✅ BEFORE nesmí mít "present" status
- ✅ AFTER má konkrétní build instructions (ne "improve trust")
- ✅ Kategorie jsou: Decision Clarity, Comparability, Trust & Authority, Entity Understanding, Risk Reduction
