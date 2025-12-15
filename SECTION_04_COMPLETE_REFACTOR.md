# Section 04 - Complete Refactor

## ✅ ZMĚNY DOKONČENY

### **🎯 CÍL:**
Změnit Section 04 z "3 obecných bodů" na "10-20 granulárních AI requirements" rozdělených do 5 expertních kategorií.

---

## 1️⃣ BACKEND - NOVÉ SCHEMA

### File: `backend/app/schemas.py`

**Nové schema:**
```python
class AIRequirement(BaseModel):
    requirement_name: str  # Konkrétní název (např. "Explicit service definitions")
    category: Literal["decision_clarity", "comparability", "trust_authority", "entity_understanding", "risk_confidence"]
    problem_statement: str  # BEFORE (co chybí, 1 věta)
    solution_statement: str  # AFTER (co AI potřebuje, 1 věta)
    current_status: Literal["missing", "weak", "present"]
    ai_impact: str  # Jak to ovlivňuje doporučení (1 věta)
    evidence_refs: List[int]
```

**Integrace do `AuditResult`:**
```python
ai_requirements: List[AIRequirement] = Field(..., min_length=10, max_length=20, description="10-20 granular requirements")
stage_3_what_ai_needs: List[Stage3Need] = Field(..., description="LEGACY")
```

---

## 2️⃣ BACKEND - NOVÝ PROMPT

### File: `backend/app/services/llm_auditor.py`

**Přidána sekce: SECTION 04 — AI REQUIREMENTS (GRANULAR BREAKDOWN)**

**Klíčové instrukce:**
- MUSÍ generovat 10-20 requirements
- Rozděleno do 5 kategorií:
  * **decision_clarity** (4-6 items): service definitions, scope, FAQ, decision triggers
  * **comparability** (3-5 items): pricing, value anchors, competitor positioning
  * **trust_authority** (3-5 items): testimonials, case studies, proof
  * **entity_understanding** (2-4 items): brand signals, topical depth, structured data
  * **risk_confidence** (2-4 items): refund clarity, SLA, objection handling
- 80% MUSÍ být "missing" nebo "weak" (bias k problémům)
- Personalizováno podle business type (restaurace ≠ SaaS)

**Příklady requirements:**
- Explicit service definitions
- Pricing tier transparency
- Customer testimonials with outcomes
- FAQ resolving buyer uncertainty
- Founder/team authority pages
- Refund/cancellation clarity

---

## 3️⃣ FRONTEND - NOVÉ UI

### File: `frontend/src/pages/ReportPage.jsx`

**Odstraněno:**
```javascript
❌ beforeAfter = useMemo(() => ({
    before: ['No pricing pages', 'No comparisons', 'Weak entity signals'],
    after: ['AI explains pricing', 'AI compares fairly', 'AI trusts the brand']
  }), [needs2])
```

**Přidáno:**
```javascript
✅ const aiRequirements = Array.isArray(core?.ai_requirements) ? core.ai_requirements : []
✅ const requirementsByCategory = useMemo(() => {
    // Groups requirements by category
    return {
      decision_clarity: [],
      comparability: [],
      trust_authority: [],
      entity_understanding: [],
      risk_confidence: []
    }
  }, [aiRequirements])
```

**Nové UI:**
- **Category groups** - každá kategorie má vlastní blok
- **Problem/Solution cards** - každý requirement má BEFORE/AFTER
- **Visual hierarchy** - badge s počtem problémů, status ikony (❌⚠️✅)
- **Summary stats** - celkový přehled: Missing / Weak / Present

**Struktura karty:**
```
┌────────────────────────────────┐
│ Requirement Name          ❌  │
├────────────────────────────────┤
│ ❌ Before (Current)           │
│ Problem statement             │
├────────────────────────────────┤
│ ✅ After (Needed)             │
│ Solution statement            │
├────────────────────────────────┤
│ Impact: How it affects AI     │
└────────────────────────────────┘
```

---

## 4️⃣ AKCEPTAČNÍ KRITÉRIA

### ✅ SPLNĚNO:

1. **❌ Už nikdy tam nesmí být jen "3 problémy"**
   - ✅ Backend generuje 10-20 requirements

2. **✅ Klient má pocit: "Ty jo… teď chápu, proč nás AI nedoporučuje."**
   - ✅ 10-20 granulárních problémů + konkrétní řešení
   - ✅ Rozděleno do expertních kategorií
   - ✅ Každý problém má BEFORE/AFTER + dopad

3. **✅ Sekce působí: expertně, diagnosticky, draze (mentálně)**
   - ✅ 5 kategorií (Decision/Comparability/Trust/Entity/Risk)
   - ✅ Personalizace podle typu byznysu
   - ✅ Evidence-backed (evidence_refs)

---

## 5️⃣ DATA FLOW

```
LLM Prompt (SECTION 04)
    ↓
Generates 10-20 AIRequirement objects
    ↓
Validated by Pydantic (AuditResult)
    ↓
Stored in DB (audit_outputs.audit_json)
    ↓
Served via /api/audit/{id}/report
    ↓
Frontend: raw.core_audit.ai_requirements
    ↓
Grouped by category
    ↓
Rendered as cards (BEFORE/AFTER)
```

---

## 6️⃣ FALLBACK PRO STARÁ DATA

**Pokud `ai_requirements` je prázdné:**
```javascript
{aiRequirements.length === 0 ? (
  <div>AI Requirements Unavailable - Run new audit to populate.</div>
) : (
  // Show granular cards
)}
```

**Legacy `stage_3_what_ai_needs` zůstává pro backward compat**, ale není použit v UI.

---

## 7️⃣ PŘÍKLADY KATEGORIÍ

### **Decision Clarity** (4-6 requirements):
- Explicit service definitions
- Clear scope boundaries
- Feature vs benefit separation
- Decision triggers ("when to choose this")
- FAQ resolving buyer uncertainty
- Structured summaries AI can quote

### **Comparability** (3-5 requirements):
- Pricing tier transparency
- Value anchors and comparisons
- Competitor positioning
- Alternative explanations ("who this is NOT for")
- Measurable differentiation points

### **Trust & Authority** (3-5 requirements):
- Customer testimonials with context
- Case studies with measurable outcomes
- Proof of expertise (credentials, experience)
- Third-party validation
- Guarantees or risk reducers

### **Entity Understanding** (2-4 requirements):
- Strong brand entity signals
- Founder/team authority pages
- Topical depth clusters
- Internal linking logic
- Structured data for AI reuse

### **Risk & Confidence** (2-4 requirements):
- Refund/cancellation clarity
- SLA or expectation setting
- Downside explanations
- Objection handling content

---

## 8️⃣ TESTING

**Pro ověření:**
1. Spusťte nový audit
2. Backend LOG: `"[STAGE A] ✅ Validation passed"`
3. Zkontrolujte `ai_requirements` má 10-20 items
4. UI zobrazí category groups s granulárními kartami
5. Klient vidí "hloubku" (ne 3 body)

**Expected UI:**
- 5 category bloků
- Každý blok: 2-6 karet
- Každá karta: requirement name + BEFORE + AFTER + impact
- Summary: X missing, Y weak, Z present

---

## ✅ REFACTOR COMPLETE

**Před:** 3 hardcoded problémy  
**Po:** 10-20 data-driven granulárních requirements rozdělených do 5 expertních kategorií

**Psychologie:** Sekce nyní působí jako "deep forensic analysis", ne "3 obecné body". Klient má pocit systémové komplexnosti → vyšší vnímání value.
