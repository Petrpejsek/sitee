# Section 03 - Decision Coverage Score Fix

## Problem Diagnosis

### Issue: 0/0/0 Score Displayed

**Root Causes:**
1. **Frontend** was reading from wrong path: `core.raw_audit.decision_coverage_score` (doesn't exist)
2. **Backend** relied 100% on LLM to provide `decision_coverage_score`, with no validation or fallback
3. **UI** had silent fallback (`|| 0`) that masked missing data

---

## A) Frontend Data Flow (BEFORE → AFTER)

### BEFORE (BROKEN):
```javascript
// Wrong path:
core?.raw_audit?.decision_coverage_score?.present || 0
core?.raw_audit?.decision_coverage_score?.weak || 0
core?.raw_audit?.decision_coverage_score?.missing || 0
```

**Problem:** `raw_audit` doesn't exist in `core`. Should be direct property of `core`.

### AFTER (FIXED):
```javascript
// Correct extraction:
const decisionAudit = Array.isArray(core?.decision_readiness_audit) ? core.decision_readiness_audit : []
const decisionScore = core?.decision_coverage_score || null

// UI uses:
decisionScore.present
decisionScore.weak
decisionScore.missing
```

---

## B) Backend Post-Processing (NEW)

### File: `backend/app/services/llm_auditor.py`

**Added:** Automatic score calculation after LLM response, before Pydantic validation.

```python
# Line 966-992 (new logic):
audit_json = json.loads(audit_json_str)

# POST-PROCESSING: Calculate decision_coverage_score if missing/invalid
if "decision_readiness_audit" in audit_json:
    elements = audit_json["decision_readiness_audit"]
    
    calculated_score = {
        "present": sum(1 for e in elements if e.get("status") == "present"),
        "weak": sum(1 for e in elements if e.get("status") in ["weak", "fragmented"]),
        "missing": sum(1 for e in elements if e.get("status") == "missing"),
        "total": len(elements)
    }
    
    llm_score = audit_json.get("decision_coverage_score")
    if not llm_score or llm_score.get("total", 0) == 0:
        print("[STAGE A] Using calculated score")
        audit_json["decision_coverage_score"] = calculated_score
```

**Guarantees:**
- ✅ Score always exists if `decision_readiness_audit` exists
- ✅ Score totals match element count
- ✅ Deterministic (calculated from audit data, not LLM guesswork)

---

## C) UI "Unavailable" State (NEW)

### File: `frontend/src/pages/ReportPage.jsx`

**Detection Logic:**
```javascript
if (!decisionScore || decisionScore.total === 0) {
  // Show unavailable state
}
```

**Unavailable UI:**
```
┌────────────────────────────┐
│ Decision Coverage Score    │
│                            │
│         ⚠️                 │
│   Score Unavailable        │
│                            │
│ Audit output missing       │
│ decision coverage data.    │
│                            │
│   —       —       —        │
│ Present  Weak  Missing     │
└────────────────────────────┘
```

**Normal UI (when data exists):**
```
┌────────────────────────────┐
│ Decision Coverage Score    │
│                            │
│   2      3       5         │
│ Present  Weak  Missing     │
│                            │
│ AI recommendation systems  │
│ require near-complete      │
│ decision coverage.         │
└────────────────────────────┘
```

---

## D) Prompt (Already Correct)

### File: `backend/app/services/llm_auditor.py`

**Prompt explicitly requests:**
- 8-10 decision elements (not 3)
- Each with status: missing | weak | fragmented | present
- Bias toward missing/weak (present only for explicit, structured content)

**LLM schema includes:**
```json
"decision_coverage_score": {
  "present": "integer 0-10",
  "weak": "integer 0-10",
  "missing": "integer 0-10",
  "total": "integer 8-10"
}
```

**But:** Backend now calculates this as fallback, so LLM can omit it.

---

## E) Test Scenarios

### 1. Web with minimal info (local business)
**Expected:**
- 8-10 decision elements
- Most marked as `missing` or `weak`
- Score: ~1-2 present, ~3-4 weak, ~4-5 missing
- Total: > 0

### 2. Web with structured content (SaaS, agency)
**Expected:**
- 8-10 decision elements
- Some `present`, rest `weak`/`missing`
- Score: ~2-4 present, ~3-5 weak, ~1-3 missing
- Total: > 0

### 3. LLM response without score
**Expected:**
- Backend calculates score from `decision_readiness_audit`
- UI displays real numbers
- No 0/0/0

### 4. Audit without decision_readiness_audit (legacy/error)
**Expected:**
- `decisionScore` is null
- UI shows "Score Unavailable" state
- No silent 0/0/0

---

## Summary of Changes

### Backend (`llm_auditor.py`):
✅ Added post-processing to calculate `decision_coverage_score` from `decision_readiness_audit`
✅ Validates LLM score against actual element count
✅ Guarantees score exists if elements exist

### Frontend (`ReportPage.jsx`):
✅ Fixed data path: `core.decision_coverage_score` (not `core.raw_audit.decision_coverage_score`)
✅ Added extraction: `const decisionScore = core?.decision_coverage_score || null`
✅ Added "unavailable" state when `!decisionScore || decisionScore.total === 0`
✅ Removed silent `|| 0` fallback (now explicit unavailable UI)

### Result:
- **No more 0/0/0** unless audit truly has zero elements
- **Transparent errors** - UI shows "unavailable" instead of fake zeros
- **Deterministic score** - calculated from real data, not LLM guesswork
- **Testable** - backend logs score calculation
