# AI Visibility Sales Report – Implementation Summary

**Date:** December 12, 2025  
**Status:** ✅ Implementation Complete

## Overview

The LLM Audit Engine has been **completely transformed** from an analytics-style audit report into a **sales-focused AI Visibility Report** designed to sell page-building services. This is no longer a neutral technical audit—it's a sales weapon.

---

## 🎯 Key Philosophy Changes

### BEFORE (Old Approach)
- **Neutral analyst** tone
- **Technical SEO language** (coverage, scores, frameworks)
- **Audit mindset** (analyze and report)
- **2-stage pipeline** (Stage A: audit, Stage B: action plan)

### AFTER (New Sales-Flow Approach)
- **Sales consultant** tone
- **Business outcome language** (traffic, leads, visibility)
- **Sales mindset** (create desire → present solution → close)
- **Unified 5-stage report** (A-E in single LLM call)

---

## 📋 Implementation Details

### 1. **System Prompt Transformation**
**File:** `backend/app/services/llm_auditor.py`

**Changed From:**
```
You are an expert analyst of LLM-driven recommendations...
```

**Changed To:**
```
You are not an SEO analyst.
You are an AI visibility consultant whose job is to explain
why AI models (ChatGPT, Gemini, Perplexity) do or do not recommend a business,
and what must be built to fix it.

Your output will be used as a SALES document.
Not an audit. Not a technical report.
```

**Key Rules Enforced:**
- ❌ NO SEO terminology
- ❌ NO "page missing" language
- ❌ NO neutral tone
- ✅ Clear, direct, confident sales language
- ✅ Frame everything as barriers to AI recommendation
- ✅ Think in outcomes: "AI cannot shortlist you", "AI prefers competitors"

---

### 2. **New 5-Stage Sales Flow (Stages A-E)**

#### **STAGE A — AI VISIBILITY STATUS (PAIN)**
- **ChatGPT visibility %** + label (Poor/Limited/Strong)
- **Gemini visibility %** + label
- **Perplexity visibility %** + label
- **Hard sentence:** "AI models are unlikely to recommend this business today."

**Visual:** 3 big donut charts (red/orange/green)

#### **STAGE B — WHY AI DOES NOT RECOMMEND THEM (CAUSE)**
Up to 5 blockers, each with:
- **What is missing** on the site
- **What AI cannot do** because of it
- **Severity:** high | medium

**Tone:** Factual, cold, unavoidable (like explaining to a restaurant owner)

#### **STAGE C — WHAT AI NEEDS TO RECOMMEND THEM (SOLUTION)**
Content TYPES (not page titles):
- Service explanation pages
- Pricing & value pages
- Comparison pages
- Entity & trust pages

For each: **what it unlocks** for AI models

#### **STAGE D — WHAT WE WILL BUILD (PACKAGES)**
3 tiers with SALES labels:

**🟠 Starter** — "AI Understands You"
- 4–6 pages
- AI can describe your business
- Still rarely recommends

**🟢 Growth** — "AI Recommends You"
- 8–12 pages
- AI compares & suggests you
- Visible in AI answers

**🔵 Authority** — "AI Prefers You"
- 15–25 pages
- AI cites & recommends confidently
- Long-term AI traffic channel

#### **STAGE E — BUSINESS IMPACT & DECISION (CLOSE)**
- **Recommended package** (based on visibility)
- **Clear outcome**
- **What staying invisible costs**
- **What changes after building**
- **Why this compounds over time**
- **Urgency statement:** "AI models update continuously – staying invisible compounds over time"

**CTA Buttons:**
- ✅ "Fix AI visibility"
- ✅ "Build AI-ready pages"
- ✅ "Start AI traffic channel"
- ❌ "Unlock full plan" (generic, removed)

---

### 3. **JSON Schema Update**
**File:** `backend/app/schemas.py`

**New Pydantic Models:**
```python
class AIVisibilityStatus(BaseModel):  # Stage A
    chatgpt_visibility_percent: int
    chatgpt_label: Literal["Poor", "Limited", "Strong"]
    gemini_visibility_percent: int
    gemini_label: Literal["Poor", "Limited", "Strong"]
    perplexity_visibility_percent: int
    perplexity_label: Literal["Poor", "Limited", "Strong"]
    hard_sentence: str

class Blocker(BaseModel):  # Stage B
    what_is_missing: str
    what_ai_cannot_do: str
    severity: Literal["high", "medium"]

class ContentNeed(BaseModel):  # Stage C
    content_type: str
    what_it_unlocks: str

class Packages(BaseModel):  # Stage D
    starter: PackageStarter
    growth: PackageGrowth
    authority: PackageAuthority

class Recommendation(BaseModel):  # Stage E
    recommended_package: Literal["starter", "growth", "authority"]
    outcome: str
    invisibility_cost: str
    change_after_building: str
    why_compounds: str
    urgency_statement: str

class AuditResult(BaseModel):
    """AI Visibility Sales Report (Stages A-E)"""
    stage_a_visibility: AIVisibilityStatus
    stage_b_blockers: List[Blocker]
    stage_c_content_needs: List[ContentNeed]
    stage_d_packages: Packages
    stage_e_recommendation: Recommendation
    appendix: Appendix
```

---

### 4. **HTML Template Redesign**
**File:** `backend/app/templates/audit_report.html`

**PAGE 1 — AI VISIBILITY STATUS (PAIN)**
- 3 big donut charts for ChatGPT, Gemini, Perplexity
- Color-coded: 🔴 Poor | 🟠 Limited | 🟢 Strong
- Hard sentence callout in red card

**PAGE 2 — WHY AI DOES NOT RECOMMEND YOU**
- Up to 5 blocker cards (red for high, orange for medium)
- Each card shows: what's missing + what AI cannot do

**PAGE 3 — WHAT AI NEEDS TO RECOMMEND YOU**
- 6 content type cards (green)
- Each shows: content type + what it unlocks for AI

**PAGE 4 — WHAT WE WILL BUILD (PACKAGES)**
- 3 package cards: Starter (🟠), Growth (🟢), Authority (🔵)
- Recommended package highlighted
- Clear page counts + AI capabilities

**PAGE 5 — BUSINESS IMPACT & DECISION**
- Recommended package callout (green)
- Cost of staying invisible (red)
- What changes after building (green)
- Why it compounds (gray)
- Urgency statement (orange)
- **CTA button:** "→ Build AI-Ready Pages"

---

### 5. **Backward Compatibility Layer**
**File:** `backend/app/services/llm_auditor.py`

**Function:** `_convert_sales_to_action_plan()`

**Purpose:** Convert new sales structure → old action plan format

This ensures:
- ✅ Existing API endpoints continue to work
- ✅ Frontend dashboard continues to work
- ✅ Report generator can render both old and new reports
- ✅ No breaking changes for existing integrations

**Mapping:**
- `recommended_package: "starter"` → `coverage_level: "baseline"`
- `recommended_package: "growth"` → `coverage_level: "recommended"`
- `recommended_package: "authority"` → `coverage_level: "authority"`

---

### 6. **Pipeline Changes**
**File:** `backend/app/worker.py`

**Before:**
```
[STAGE A] Core Audit (scoring + gaps)
[STAGE B] Action Plan Builder (pages + outlines)
```

**After:**
```
[STAGE A] AI Visibility Sales Report (Stages A-E)
  ↳ ChatGPT visibility: 25% (Poor)
  ↳ Blockers: 5
  ↳ Recommended package: growth
```

**Note:** Stage B is now DISABLED for new sales flow. All 5 stages (A-E) are generated in a single LLM call for consistency and speed.

---

## 🎨 Visual & UX Rules (ENFORCED)

### COLOR SYSTEM
```
--red:    #dc2626   → AI cannot do / risk / blocker
--orange: #f59e0b   → partial / limited / weak
--green:  #16a34a   → strong / unlocked / ready
--gray:   #9ca3af   → inactive / future / not yet
```

### LAYOUT PRINCIPLES
1. **Big charts first, text second**
2. **Red/orange/green everywhere**
3. **One idea per screen section**
4. **White space = confidence**
5. **No internal terminology visible early**
6. **Everything must look expensive & intentional**

### DO NOTs (ABSOLUTE)
🚫 NO generic dashboards  
🚫 NO analytics language  
🚫 NO "coverage units" first  
🚫 NO walls of text  
🚫 NO neutral tone  

---

## 🧪 Testing & Validation

### To Test the New Sales Flow:

1. **Start the worker:**
```bash
cd backend
source venv/bin/activate
python -m app.worker
```

2. **Submit a test audit:**
```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "target_domain": "example.com",
    "competitor_domains": [],
    "locale": "en-US",
    "company_description": "Test business",
    "products_services": "Test services"
  }'
```

3. **Check the report:**
- PDF: `backend/reports/audit_{job_id}.pdf`
- HTML: `backend/reports/audit_{job_id}.html`
- Web dashboard: `http://localhost:5173/report/{job_id}?access=preview`

### Expected Output:
- ✅ 3 donut charts on page 1
- ✅ Blocker cards on page 2
- ✅ Content need cards on page 3
- ✅ Package tiers on page 4
- ✅ CTA section on page 5
- ✅ No SEO terminology anywhere
- ✅ Sales-focused language throughout

---

## 📊 Success Criteria

Before considering this complete, verify:

✅ **A restaurant owner understands this**  
✅ **A lawyer understands this**  
✅ **A plumber understands this**  

**Correct explanation should be:**
> "AI doesn't show us. These guys will fix it by building the right pages."

If a non-technical founder can't explain the report in 1 sentence → ❌ FAIL

---

## 🔒 Final Note

This report is now the **core monetization engine** of sitee.ai.

Every pixel must answer:
> **"Why should I pay you to fix my AI visibility?"**

Do not optimize for beauty.  
Optimize for **desire + inevitability**.

---

## 📂 Files Modified

### Core Logic
- ✅ `backend/app/services/llm_auditor.py` (system prompt + schema + pipeline)
- ✅ `backend/app/schemas.py` (Pydantic models)
- ✅ `backend/app/worker.py` (print statements)

### Templates
- ✅ `backend/app/templates/audit_report.html` (complete redesign)

### Backward Compatibility
- ✅ `backend/app/services/report_generator.py` (already handles both structures)
- ✅ Frontend continues to work unchanged (uses normalized payload)

---

## 🚀 Next Steps

1. **Test with real domain** to verify LLM generates proper sales language
2. **Iterate on prompt** if LLM returns neutral/technical language
3. **Adjust package labels** based on customer feedback
4. **Add CTA tracking** to measure conversion from report → purchase
5. **A/B test urgency statements** to optimize close rates

---

## 💡 Key Insight

**This is consulting-style selling, not SaaS metrics.**

The report creates discomfort (loss), clarity (cause), desire (solution), and inevitability (urgency) — then closes with packages.

AI models are framed as a **NEW TRAFFIC CHANNEL**, not a technical optimization opportunity.

---

**Implementation Complete ✅**


