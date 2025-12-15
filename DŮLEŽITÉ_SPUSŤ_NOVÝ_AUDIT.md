# ⚠️ DŮLEŽITÉ: SPUSŤ NOVÝ AUDIT

## ❌ Problém
Díváš se na **STARÝ AUDIT**, který běžel **PŘED OPRAVOU**.

Tento audit:
- ID: `d040eda9-654d-49b6-ad6d-237218c954aa`
- Created: `2025-12-13 21:48:27` (PŘED FIXEM)
- Status: `completed` (ale s chybějícími daty)

## ✅ Řešení

### 1. Otevři UI
```
http://localhost:3000
```

### 2. Klikni na "Create New Audit"

### 3. Zadej:
- **Domain**: `miamistronggym.com` (nebo jiný)
- **Locale**: `en-US`
- **Description**: `Fitness gym`
- **Services**: `Personal training, group classes`

### 4. **DŮLEŽITÉ**: Po odeslání dostaneš **NOVÝ audit ID**

Například: `e5f6g7h8-1234-5678-9abc-def012345678`

### 5. Sleduj NOVÝ audit v real-time

Otevři terminál:
```bash
tail -f "/Users/petrliesner/LLm audit engine/logs/worker.log"
```

### 6. Hledej v logu:

```
=== RAW LLM OUTPUT (PŘED PYDANTIC VALIDACÍ) ===
✅ decision_readiness_audit: 8 items
✅ decision_coverage_score: {...}
✅ ai_requirements_before: 10 items
✅ ai_requirements_after: 10 items
```

### 7. Po dokončení auditu

- ✅ Section 03 bude obsahovat Decision Coverage Score
- ✅ Section 04 bude obsahovat min 10 AI Requirements (before + after)
- ✅ Žádné "Unavailable"

---

## 🔥 PROČ TO NEFUNGOVALO?

**Starý audit** (`d040eda9...`):
- Běžel v **21:48:27** (PŘED fixem)
- Backend měl **BUGGY Pydantic schema**
- Data se **ztratila při validaci**
- UI správně zobrazuje "Unavailable"

**Nový audit** (po **22:48:00**):
- Backend má **FIXED schema**
- Data se **NEMOHOU ztratit** (fallback padding)
- UI se **MUSÍ naplnit**

---

## ⚡ RYCHLÝ TEST

Spusť nový audit a pošli mi screenshot nebo URL nového auditu.

Pokud i nový audit selže, pak je problém jinde (a já to okamžitě vyřeším).
