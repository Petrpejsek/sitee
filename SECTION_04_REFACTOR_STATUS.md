# Section 04 Refactor - Summary

## ✅ BACKEND CHANGES COMPLETE:

### 1. New Schema (`schemas.py`):
```python
class AIRequirement(BaseModel):
    requirement_name: str  # e.g., "Explicit service definitions"
    category: Literal["decision_clarity", "comparability", "trust_authority", "entity_understanding", "risk_confidence"]
    problem_statement: str  # BEFORE (what's missing)
    solution_statement: str  # AFTER (what's needed)
    current_status: Literal["missing", "weak", "present"]
    ai_impact: str
    evidence_refs: List[int]
```

### 2. Updated `AuditResult`:
```python
ai_requirements: List[AIRequirement] = Field(..., min_length=10, max_length=20)
stage_3_what_ai_needs: List[Stage3Need] = Field(..., description="LEGACY")
```

### 3. Prompt Added (SECTION 04):
- 10-20 granular requirements
- 5 categories (decision/comparability/trust/entity/risk)
- Personalized by business type
- 80% must be missing/weak (conservative bias)

---

## ⏳ FRONTEND STATUS:

**Problem:** Old Section 04 uses hardcoded `beforeAfter` with only 3 items.

**Solution in progress:**  
Due to file size, need to complete frontend refactor in next session.

**Changes needed:**
1. Remove `beforeAfter` hardcoded logic (lines 252-264)
2. Add `aiRequirements` extraction (line ~163)  
3. Add category grouping logic
4. Replace entire Section 04 UI (lines 1225-1298) with granular cards grouped by category

---

## Next Steps:
Complete frontend refactor to display 10-20 granular requirements grouped by category.
