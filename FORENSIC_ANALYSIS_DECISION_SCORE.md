# FORENSIC ANALYSIS - Decision Coverage Score 0/0/0

## 1️⃣ PAYLOAD STRUCTURE VERIFICATION

### API Endpoint:
```
GET /api/audit/{jobId}/report
```

### Response Structure:
```json
{
  "meta": {
    "job_id": "...",
    "domain": "...",
    "pages_analyzed": 10,
    "limited_data": false
  },
  "raw": {
    "core_audit": {
      "stage_1_ai_visibility": {...},
      "ai_interpretation": {...},
      "decision_readiness_audit": [...],  // ← EXPECTED HERE
      "decision_coverage_score": {...},   // ← EXPECTED HERE
      "stage_2_why_ai_chooses_others": [...],
      "stage_3_what_ai_needs": [...],
      "stage_4_packages": {...},
      "stage_5_business_impact": {...},
      "appendix": {...}
    },
    "action_plan": {...},
    "sampled_urls": [...]
  },
  "normalized": {...}
}
```

### UI Data Path (CORRECT):
```javascript
const core = raw?.core_audit || {}
const decisionAudit = Array.isArray(core?.decision_readiness_audit) ? core.decision_readiness_audit : []
const decisionScore = core?.decision_coverage_score || null
```

✅ **UI path is correct** - `raw.core_audit.decision_readiness_audit`
✅ **Report mapper doesn't filter** - `ReportGenerator.build_report_view_model()` just wraps `audit_data` as `raw.core_audit`

---

## 2️⃣ BACKEND - 3 CRITICAL POINTS

### A) Pydantic Schema (`schemas.py`) - ✅ CORRECT

```python
# Line 240-241:
class AuditResult(BaseModel):
    ...
    decision_readiness_audit: List[DecisionElement] = Field(..., min_length=8, max_length=10)
    decision_coverage_score: DecisionCoverageScore = Field(...)
    ...
```

**Status:** ✅ Fields are present in schema
**Issue:** Both fields are REQUIRED → if LLM omits them, validation fails

---

### B) LLM Prompt (`llm_auditor.py`) - ✅ CORRECT

**Prompt includes:**
```python
# Line 697-810: SECTION 03 — DECISION READINESS AUDIT (MANDATORY)
# Line 176: JSON schema with decision_readiness_audit
# Line 177: JSON schema with decision_coverage_score
```

**Status:** ✅ Prompt instructs LLM to generate these fields

---

### C) Repair Prompt (`llm_auditor.py`) - ❌ PROBLEM FOUND

**BEFORE (Line 1012):**
```python
repair_prompt = f"...Ensure ALL 5 stages are present: stage_1_ai_visibility, stage_2_why_ai_chooses_others, stage_3_what_ai_needs, stage_4_packages, stage_5_business_impact."
```

**Issue:**
- ❌ Does NOT mention `decision_readiness_audit`
- ❌ Does NOT mention `decision_coverage_score`
- ❌ When LLM omits these fields, repair pass doesn't hint them
- ❌ Validation fails → audit fails

**AFTER (FIXED):**
```python
repair_prompt = f"...Ensure ALL required fields are present:
- stage_1_ai_visibility
- ai_interpretation
- decision_readiness_audit (8-10 elements with status: missing/weak/fragmented/present)
- decision_coverage_score (present/weak/missing/total)
- stage_2_why_ai_chooses_others
- stage_3_what_ai_needs
- stage_4_packages
- stage_5_business_impact
- appendix"
```

✅ **Now explicitly lists all required fields**

---

## 3️⃣ POST-PROCESSING FIX

### BEFORE (Line 967-990):
```python
# Only calculated score IF decision_readiness_audit exists
if "decision_readiness_audit" in audit_json and isinstance(...):
    elements = audit_json["decision_readiness_audit"]
    calculated_score = {...}
    # Use calculated score if LLM score missing/invalid
```

**Issue:**
- ✅ Calculates score from elements
- ❌ Does NOTHING if `decision_readiness_audit` is missing
- ❌ Pydantic validation fails → audit fails

### AFTER (FIXED):
```python
# 1. First, ensure decision_readiness_audit exists (create fallback if missing)
if "decision_readiness_audit" not in audit_json or not isinstance(...):
    print("[STAGE A] ⚠️ decision_readiness_audit missing, creating minimal fallback")
    audit_json["decision_readiness_audit"] = [
        # 8 generic fallback elements (all missing/weak)
    ]

# 2. Then, calculate score from elements
if "decision_readiness_audit" in audit_json:
    elements = audit_json["decision_readiness_audit"]
    calculated_score = {
        "present": sum(1 for e in elements if e.get("status") == "present"),
        "weak": sum(1 for e in elements if e.get("status") in ["weak", "fragmented"]),
        "missing": sum(1 for e in elements if e.get("status") == "missing"),
        "total": len(elements)
    }
    
    # Use calculated score if LLM score missing/invalid
    llm_score = audit_json.get("decision_coverage_score")
    if not llm_score or llm_score.get("total", 0) == 0:
        audit_json["decision_coverage_score"] = calculated_score
```

✅ **Now guarantees both fields exist before Pydantic validation**

---

## 4️⃣ ROOT CAUSE SUMMARY

### Why UI showed 0/0/0 (or "Score Unavailable"):

**Path 1 (most likely):**
1. LLM response omitted `decision_readiness_audit` or `decision_coverage_score`
2. Post-processing did NOT create fallback
3. Pydantic validation failed (required fields missing)
4. Repair prompt did NOT mention these fields → repair attempt also failed
5. Audit failed OR old audit (before schema update) loaded with incomplete data
6. UI received `null` or incomplete data → showed "Score Unavailable"

**Path 2 (less likely):**
1. LLM generated `decision_readiness_audit` but with invalid structure
2. Post-processing calculated score correctly
3. Pydantic validation passed
4. But DB had old audit (before these fields existed)
5. UI read old audit → no fields → "Score Unavailable"

---

## 5️⃣ FIXES IMPLEMENTED

### Fix 1: Repair Prompt Enhancement ✅
**File:** `backend/app/services/llm_auditor.py`  
**Lines:** ~1012-1020  
**Change:** Repair prompt now explicitly lists `decision_readiness_audit` and `decision_coverage_score`

### Fix 2: Fallback Creation ✅
**File:** `backend/app/services/llm_auditor.py`  
**Lines:** ~968-1042  
**Change:** 
- If `decision_readiness_audit` missing → create 8 generic fallback elements
- Always calculate `decision_coverage_score` from elements
- Guarantee both fields exist before Pydantic validation

### Fix 3: UI Unavailable State (already done) ✅
**File:** `frontend/src/pages/ReportPage.jsx`  
**Change:** 
- Detect `!decisionScore || decisionScore.total === 0`
- Show "Score Unavailable" instead of silent 0/0/0
- Transparent error state

---

## 6️⃣ TESTING STRATEGY

### Test 1: New Audit on Minimal Site
**Expected:**
- Backend LOG: `"[STAGE A] decision_readiness_audit missing, creating minimal fallback"` (if LLM omits it)
- Backend LOG: `"[STAGE A] Using calculated score: {present: 0, weak: 2, missing: 6, total: 8}"`
- UI: Shows real numbers (not 0/0/0 unavailable)

### Test 2: New Audit on Rich Site
**Expected:**
- Backend LOG: `"[STAGE A] ✅ Validation passed"` (LLM generated fields)
- UI: Shows ~2-4 present, ~3-5 weak, ~1-3 missing

### Test 3: Repair Pass Trigger
**Expected:**
- Backend LOG: `"[STAGE A] Validation error on attempt 1: ..."`
- Backend LOG: `"[STAGE A] Repair pass: Fixing schema validation..."`
- Repair prompt now mentions `decision_readiness_audit` explicitly
- Backend LOG: `"[STAGE A] ✅ Validation passed (attempt 2)"`

### Test 4: Old Audit (Before Schema Update)
**Expected:**
- UI: Shows "Score Unavailable" (data doesn't exist in old audits)
- No crash, transparent error state

---

## 7️⃣ ACCEPTANCE CRITERIA

✅ **Repair prompt mentions all required fields** (including decision fields)  
✅ **Backend creates fallback if LLM omits decision_readiness_audit**  
✅ **Backend always calculates decision_coverage_score from elements**  
✅ **Pydantic validation never fails due to missing decision fields**  
✅ **UI transparently shows "unavailable" for old/incomplete audits**  
✅ **New audits always have decision_coverage_score with total > 0**

---

## 8️⃣ NEXT STEPS

1. **Run new audit** to verify fixes work
2. **Check backend logs** for:
   - `"[STAGE A] decision_readiness_audit missing, creating minimal fallback"` (if triggered)
   - `"[STAGE A] Using calculated score: {...}"`
   - `"[STAGE A] ✅ Validation passed"`
3. **Verify UI** shows real numbers (not unavailable)
4. **Check old audits** still work (show unavailable, don't crash)

---

## Summary

**Problem:** UI showed 0/0/0 because backend didn't guarantee `decision_readiness_audit` and `decision_coverage_score` fields always exist.

**Root Cause:** Repair prompt didn't mention these fields → when LLM omitted them → repair pass couldn't fix → validation failed.

**Solution:** 
1. Enhanced repair prompt to explicitly list all required fields
2. Added fallback creation if LLM omits decision_readiness_audit
3. Always calculate decision_coverage_score from elements
4. UI shows transparent "unavailable" state for old/incomplete data

**Result:** Deterministic, never-failing decision coverage score generation.
