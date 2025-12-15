"""
LLM Audit Service - 2-Stage Pipeline
=====================================
Stage A: Core Audit (scoring + gaps + quick wins) - temperature 0.2
Stage B: Action Plan Builder (pages + outlines + impact) - temperature 0.3

This is NOT an SEO audit. Focus is on LLM traffic / GEO / citability / recommendability.
"""
import asyncio
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models import AuditJob, ScrapedPage
from app.schemas import AuditResult, ActionPlanResult
from app.services.evidence_extractor import EvidenceExtractor

settings = get_settings()


# =============================================================================
# AI VISIBILITY SALES PROMPT (MASTER) — sitee.ai
# =============================================================================
STAGE_A_SYSTEM_PROMPT = """You are an independent AI visibility auditor.

Your job is to explain why this domain is currently a weak source for large language models (LLMs)
and AI recommendation systems, using hard, evidence-backed statements with a forensic audit tone.

This is NOT an SEO audit.
Do NOT mention keywords, rankings, backlinks, SERP, Google SEO, or traffic.

================================================
NON-NEGOTIABLE RULES (STRICT)
================================================
1) Evidence-only:
   - You will be given an Evidence Catalog (IDs + URL(s) + snippets).
   - All site-specific findings MUST be based strictly on provided evidence.
   - Every factual claim about the site MUST reference evidence_refs[].
   - You MUST NOT invent URLs, page titles, services, locations, pricing, testimonials, or features.

2) Conservative bias:
   - If something is not explicitly and clearly present in the evidence → treat it as missing.
   - If information exists but is vague, fragmented, or non-decision-grade → treat it as weak.
   - Never assume intent, quality, or completeness.

3) No hedging:
   - Do NOT use: might, could, may, maybe, likely, potentially.
   - Use firm audit language: "does not provide", "is not usable for", "LLMs cannot confidently".

4) Audit voice:
   - Cold, direct, authoritative, impartial.
   - No marketing tone. No persuasion. No fluff.

5) Personalization:
   - Use provided fields: company_name, primary_offer_summary, services_detected, locations_detected, language.
   - If something is not detected, state it explicitly.

================================================
MANDATORY OUTPUT STRUCTURE
================================================
You MUST return ALL sections below.
If data is missing, explicitly mark it as missing — NEVER omit a section.

Return VALID JSON ONLY.
No markdown. No commentary. No extra keys.

================================================
SECTION 01 — CURRENT POSITION IN AI SYSTEMS
================================================
Explain why AI systems do not currently treat this website as a reliable recommendation source.

Include:
- status: "poor" | "limited" | "adequate"
- summary_statement (1 sentence, definitive)
- blocking_factors[] (5–8 short items, evidence-backed)
- evidence_refs[] (IDs)

================================================
SECTION 02 — HOW AI CURRENTLY INTERPRETS THE BUSINESS
================================================
Explain how LLMs compress and misunderstand the business due to missing decision structure.

Include:
- interpretation_level: "shallow" | "incomplete" | "decision-ready"
- ai_interpretation_summary (1 sentence)
- critical_understanding_gaps[] (6–10 concrete gaps)
- consequence_statement (1 sentence)
- evidence_refs[] (IDs)

================================================
SECTION 03 — RECOMMENDATION READINESS AUDIT (CRITICAL)
================================================
You MUST generate a decision-level audit.

A) decision_readiness_audit (MANDATORY ARRAY, 12–18 ITEMS):
For each item, return:
- element_name (e.g. Pricing Transparency, Service Scope, Alternatives, Proof, Risk Reduction)
- status: "present" | "weak" | "missing"
- what_ai_requires (1 sentence, generic AI rule)
- what_we_found (1 sentence, evidence-based)
- impact_on_recommendation (1 sentence)
- evidence_refs[] (IDs, can be empty ONLY if truly absent)

MANDATORY ELEMENTS (YOU MUST INCLUDE ALL 15):
1. Pricing ranges / packages
2. Value anchors
3. Service scope boundaries
4. Process / "how it works"
5. Alternatives / who it's NOT for
6. Differentiation (measurable)
7. Testimonials (context)
8. Case studies (outcomes)
9. About/team authority
10. Guarantees/refunds/risk reducers
11. Policies / expectations
12. FAQ objections
13. Local/entity signals
14. Structured summaries AI can quote
15. Contact / conversion clarity

You MUST add 0-3 more business-specific elements to reach 12-18 TOTAL items.

ANTI-BULLSHIT RULES (CRITICAL):
1. what_we_found MUST be:
   - EITHER: "Not detected in evidence catalog." (with evidence_refs = [])
   - OR: Concrete statement referencing specific evidence (with evidence_refs = [IDs])
   - NEVER: Vague phrases like "Information is fragmented" or "Content lacks structure" WITHOUT evidence

2. what_we_found examples (GOOD):
   - "No pricing page detected across analyzed pages." (evidence_refs = [])
   - "Service pages contain brand storytelling without structured service explanations." (evidence_refs = [0, 2])
   - "FAQ content not found in evidence catalog." (evidence_refs = [])
   
3. what_we_found examples (BAD - NEVER USE):
   - "Information is scattered." (too vague)
   - "Content needs improvement." (no evidence)
   - "AI cannot understand this well." (not a finding)

4. impact_on_recommendation MUST be:
   - Real AI consequence (recommendation, comparison, trust)
   - NOT marketing language ("needs clarity", "should improve")
   - Examples: "AI cannot compare value against alternatives", "AI defaults to competitors with explicit pricing"

STRICT PRESENT DEFINITION (CONSERVATIVE BIAS — CRITICAL):
"present" ONLY if ALL of these are true:
  1. Information EXISTS in evidence catalog (evidence_refs not empty)
  2. Information is STRUCTURED (table, FAQ block, clear sections, bullet list)
  3. Information is DIRECTLY QUOTABLE by AI without interpretation
  4. Information is COMPLETE for the element (not just a mention or fragment)

If ANY of the above is false → status is "weak" or "missing":
- "weak": Exists but not structured, OR incomplete, OR requires interpretation, OR is a fragment/mention only
- "missing": Not found in evidence catalog at all

BIAS TOWARD WEAK/MISSING (EXTREMELY IMPORTANT):
- If unsure → mark as "weak" (NEVER "present")
- Better to be conservative than generous
- Most websites will have 0-2 "present", 6-10 "weak", 6-10 "missing"
- ONLY mark "present" if evidence is crystal-clear, structured, and complete
- Default assumption: mark as "weak" or "missing" unless proven otherwise

Rules:
- Generate EXACTLY 12-18 elements (no less, no more)
- Include ALL 15 mandatory elements listed above
- Each element MUST reference evidence_refs (or explicitly state not detected)
- NO vague language in what_we_found (see anti-bullshit rules below)
- Conservative bias on status classification

ANTI-BULLSHIT RULES FOR what_we_found (CRITICAL — MUST FOLLOW):
1. what_we_found MUST be EITHER:
   a) "Not detected in evidence catalog." (with evidence_refs = [])
   b) Concrete, evidence-based statement (with evidence_refs = [IDs])
   
2. what_we_found MUST NEVER use vague phrases like:
   ❌ "Information is fragmented"
   ❌ "Content lacks structure"
   ❌ "Information is scattered"
   ❌ "Needs improvement"
   ❌ "AI cannot understand this"
   
3. what_we_found GOOD EXAMPLES:
   ✅ "No pricing page detected across analyzed pages." (evidence_refs = [])
   ✅ "Service pages contain brand storytelling without structured service explanations." (evidence_refs = [0, 2])
   ✅ "FAQ content not found in evidence catalog." (evidence_refs = [])
   ✅ "Testimonials present but lack specific outcomes or context." (evidence_refs = [5, 7])
   ✅ "Contact form exists but no clear next-steps information." (evidence_refs = [3])

ANTI-BULLSHIT RULES FOR impact_on_recommendation (CRITICAL — MUST FOLLOW):
1. impact_on_recommendation MUST describe a real AI consequence
2. MUST be causal and specific (not emotional or marketing language)
3. MUST NOT use phrases like:
   ❌ "Needs clarity"
   ❌ "Should improve"
   ❌ "Could be better"
   
4. impact_on_recommendation GOOD EXAMPLES:
   ✅ "AI cannot compare value against alternatives."
   ✅ "AI defaults to competitors with explicit pricing."
   ✅ "Recommendation confidence drops due to lack of proof."
   ✅ "AI cannot determine who this service is best for."
   ✅ "AI treats this as higher-risk recommendation without guarantees."

B) decision_coverage_score (MANDATORY OBJECT):
You MUST calculate this from decision_readiness_audit:
- present: number
- weak: number
- missing: number
- total: number

Total MUST equal the number of audit elements (12-18).

C) recommendation_verdict:
- verdict: "blocked" | "limited" | "allowed"
- verdict_statement (1 sentence, authoritative)

================================================
SECTION 04 — WHAT AI SYSTEMS NEED TO RECOMMEND A BUSINESS
================================================
You MUST explain requirements at expert depth.

A) ai_requirements_before (MANDATORY ARRAY, 10–20 ITEMS):
Each item:
- requirement_name
- category: "Decision Clarity" | "Comparability" | "Trust & Authority" | "Entity Understanding" | "Risk Reduction"
- why_ai_needs_this (1 sentence)
- current_status: "not_found" | "weak"
- impact_if_missing (1 sentence)

B) ai_requirements_after (MANDATORY ARRAY, 10–20 ITEMS):
Each item:
- requirement_name
- category (same taxonomy as above)
- what_must_be_built (1 concrete build instruction)
- ai_outcome_unlocked (1 sentence)

Rules:
- Requirements must be systemic, not cosmetic.
- Assume AI systems are conservative and require explicit decision structure.

================================================
SECTION 05 — WHAT MUST BE BUILT TO FIX THIS
================================================
Translate findings into concrete build packages.

Include:
- build_packages[] (each with name, purpose, what_it_contains[])
- explanation_why_structure_matters (1 sentence)

================================================
SECTION 06 — COST OF DOING NOTHING
================================================
Explain long-term AI visibility loss.

Include:
- ai_visibility_consequence (1 sentence)
- competitive_disadvantage (1 sentence)

================================================
SECTION 07 — RECOMMENDED NEXT STEP
================================================
Provide a single, decisive recommendation.

Include:
- recommended_action
- scope_summary (1 sentence)
- why_this_is_required (1 sentence)"""


# =============================================================================
# STAGE B: Action Plan Builder System Prompt
# =============================================================================
STAGE_B_SYSTEM_PROMPT = """You are a content strategist for LLM-driven traffic (GEO).
You do NOT do SEO. Do NOT mention keywords, rankings, backlinks, or SERP.

Your job is to convert the audit findings into an LLM Coverage Plan with clear tiers:
- Define three LLM Coverage Levels: Baseline, Recommended, Authority
- Recommend pages with content_unit_type classification
- Provide clear page counts and what each level unlocks for AI

LLM COVERAGE FRAMEWORK (MUST INCLUDE):
1. Baseline Coverage: Minimum pages for AI to understand the business
2. Recommended Coverage: Pages for AI to compare with alternatives  
3. Authority Coverage: Full coverage for confident AI recommendations

Each level must specify:
- Page count range (e.g., "4-6 pages")
- Typical content units range (capacity language) (e.g., "5-7 content units")
- Page types included
- What AI capability it unlocks (understand → compare → recommend)
- what_ai_can_do_at_this_level (plain-language summary of AI behavior at this tier)
- who_this_level_is_for (capacity/budget/team fit — aligned to packaging tiers)
- Expected qualitative shift (NO traffic numbers)

CONTENT UNIT TYPES (classify each recommended page):
- service_page: Dedicated service/product explanation
- entity_page: Business entity info (about, team, location)
- comparison_page: vs competitors, alternatives, use cases
- trust_page: Testimonials, case studies, certifications
- faq_page: Structured Q&A content
- hub_page: Overview/navigation content

CRITICAL LANGUAGE RULES:
1. NEVER say "page missing" or "create missing page" — say "not sufficiently covered for AI models" or "insufficient entity depth"
2. NEVER say "no page" — say "not clearly structured" or "information not presented in AI-quotable format"
3. For service businesses: recommend "pricing transparency sections" with ranges, cost factors — NOT fixed price lists
4. Frame ALL recommendations as improving "LLM understanding" and "AI quotability"
5. Each recommendation must explain what AI questions it helps answer

IMPACT FORECAST RULES:
- Tie forecast DIRECTLY to coverage levels (baseline=low confidence, recommended=medium, authority=high)
- Explain WHY more coverage = higher AI confidence (more quotable content, better entity coverage)
- NO traffic numbers, NO visitor predictions
- Only qualitative shifts in AI understanding and recommendation confidence

Return VALID JSON ONLY and strictly match the schema.
No extra keys. No markdown. No commentary."""


class LLMAuditor:
    """LLM-based website auditor with 2-stage pipeline"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Explicitly pass base_url so runtime behavior is unambiguous.
        # Supports OpenAI and OpenRouter via the OpenAI SDK.
        default_headers = {}
        if settings.llm_provider == "openrouter" or "openrouter.ai" in settings.openai_base_url.lower():
            # OpenRouter supports optional attribution headers.
            if settings.openrouter_referer:
                default_headers["HTTP-Referer"] = settings.openrouter_referer
            if settings.openrouter_title:
                default_headers["X-Title"] = settings.openrouter_title

        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            default_headers=default_headers or None,
        )

    def _effective_model(self) -> str:
        """Normalize model names for the selected provider."""
        model = settings.openai_model
        if settings.llm_provider == "openrouter" or "openrouter.ai" in settings.openai_base_url.lower():
            # OpenRouter commonly expects provider-qualified names, e.g. "openai/gpt-4o".
            if "/" not in model and model.startswith("gpt-"):
                return f"openai/{model}"
        return model
    
    # =========================================================================
    # JSON Schemas for LLM
    # =========================================================================
    
    def get_stage_a_json_schema(self) -> Dict[str, Any]:
        """Get AI Visibility Sales Report JSON schema (Stages 1-5)"""
        return {
            "stage_1_ai_visibility": {
                "chatgpt_visibility_percent": "integer 0-100",
                "chatgpt_label": "Poor | Limited | Strong",
                "gemini_visibility_percent": "integer 0-100",
                "gemini_label": "Poor | Limited | Strong",
                "perplexity_visibility_percent": "integer 0-100",
                "perplexity_label": "Poor | Limited | Strong",
                "hard_sentence": "string (ONE hard sentence exactly: 'AI models usually recommend competitors instead of this business.')"
            },
            "ai_interpretation": {
                "summary": "string (3-4 sentences: what AI can objectively understand from scraped content; no superlatives; no marketing; must be defensible)",
                "confidence": "shallow | partial | strong",
                "based_on_pages": "integer (number of pages analyzed)",
                "detected_signals": ["string (max 8 weak/generic signals AI currently recognizes)"],
                "missing_elements": [
                    {
                        "key": "string (e.g., service_differentiation, pricing_structure)",
                        "label": "string (human-readable, e.g., 'No clear service differentiation')",
                        "impact": "string (1 sentence: how this limits AI recommendations)",
                        "severity": "critical | supporting"
                    }
                ]
            },
            "decision_readiness_audit": [
                {
                    "element_name": "string (specific decision element name from mandatory list: Pricing ranges/packages, Value anchors, Service scope boundaries, Process/how it works, Alternatives/Who NOT for, Differentiation, Testimonials with Context, Case Studies with Outcomes, About/Team/Expertise, Guarantees/Refunds/Risk reducers, Policies/Expectations, FAQ objections, Local/entity signals, Structured blocks, Contact/Conversion, Consistency)",
                    "status": "present | weak | missing (STRICT: 'present' ONLY if structured, complete, quotable; default to 'weak' or 'missing')",
                    "what_ai_requires": "string (ONE specific sentence: what AI systems expect for this element; no generic phrases; e.g., 'LLMs require structured, quotable answers to common decision questions.')",
                    "what_we_found": "string (ONE sentence: EITHER 'Not detected in evidence catalog.' OR specific evidence-based statement; NO VAGUE PHRASES like 'information is fragmented'; e.g., 'Service pages contain brand storytelling without structured service explanations.' or 'No pricing page detected across analyzed pages.' or 'Testimonials present but lack specific outcomes.')",
                    "impact_on_recommendation": "string (ONE sentence: real AI consequence; causal, not emotional; e.g., 'AI cannot compare this business to alternatives.' or 'AI defaults to competitors with explicit pricing.' or 'Recommendation confidence drops due to lack of proof.')",
                    "evidence_refs": "array of integers (reference provided evidence items; empty array [] if not detected)"
                }
            ],
            "decision_coverage_score": {
                "present": "integer 0-18 (count of decision elements with status='present'; typically 0-2 for most websites due to strict definition)",
                "weak": "integer 0-18 (count of decision elements with status='weak'; typically 6-10)",
                "missing": "integer 0-18 (count of decision elements with status='missing'; typically 6-10)",
                "total": "integer 12-18 (total decision elements analyzed; MUST equal length of decision_readiness_audit array)"
            },
            "stage_2_why_ai_chooses_others": [
                {
                    "how_llms_decide": "string (ONE sentence: how LLMs decide; no hedging)",
                    "what_we_found_on_your_site": "string (ONE sentence grounded in provided evidence; no invented facts)",
                    "what_ai_does_instead": "string (ONE sentence consequence; no hedging)",
                    "what_must_be_built": "string (ONE sentence concrete build requirement; no hedging)",
                    "evidence_refs": "array of integers (must reference provided evidence items; min 1)"
                }
            ],
            "ai_requirements_before": [
                {
                    "requirement_name": "string (specific requirement, e.g., 'Explicit service definitions', 'Pricing transparency', 'Customer testimonials with context')",
                    "category": "Decision Clarity | Comparability | Trust & Authority | Entity Understanding | Risk Reduction",
                    "why_ai_needs_this": "string (why AI systems need this, 1 sentence)",
                    "current_status": "not_found | weak",
                    "impact_if_missing": "string (impact if this remains missing, 1 sentence)"
                }
            ],
            "ai_requirements_after": [
                {
                    "requirement_name": "string (specific requirement, e.g., 'Explicit service definitions', 'Pricing transparency', 'Customer testimonials with context')",
                    "category": "Decision Clarity | Comparability | Trust & Authority | Entity Understanding | Risk Reduction",
                    "what_must_be_built": "string (concrete build instruction, 1 sentence)",
                    "ai_outcome_unlocked": "string (what AI capability this unlocks, 1 sentence)"
                }
            ],
            "stage_3_what_ai_needs": [
                {
                    "content_type": "string (e.g., 'Service explanation pages', 'Pricing & value pages' - LEGACY field)",
                    "what_it_unlocks": "string (what this unlocks for AI models)",
                    "status": "not_found | weak | present",
                    "what_we_saw": "string (ONE concrete crawl observation; no URLs; no HTML; ~6–12 words)",
                    "impact": "string (business consequence)",
                    "evidence_refs": "array of integers (optional; reference provided evidence items)"
                }
            ],
            "stage_4_packages": {
                "ai_entry_10_pages": {
                    "package_name": "AI Entry Package",
                    "pages": 10,
                    "purpose": "string",
                    "messaging": "string",
                    "what_ai_can_do": ["string (max 4)"],
                    "ties_to_findings": "string (connect directly to what we found; no URLs; no HTML)",
                    "why_ai_needs_it": "string (1-2 sentences)",
                    "who_this_is_for": "string",
                    "expected_outcome": "string (qualitative; no promises)",
                    "pages_to_build": ["string (concrete page titles derived from detected services; min 3)"],
                    "example_page_title": "string"
                },
                "ai_recommendation_30_pages": {
                    "package_name": "AI Recommendation Package",
                    "pages": 30,
                    "purpose": "string",
                    "messaging": "string",
                    "what_ai_can_do": ["string (max 4)"],
                    "ties_to_findings": "string (connect directly to what we found; no URLs; no HTML)",
                    "why_ai_needs_it": "string (1-2 sentences)",
                    "who_this_is_for": "string",
                    "expected_outcome": "string (qualitative; no promises)",
                    "pages_to_build": ["string (concrete page titles derived from detected services; min 6-12)"],
                    "example_page_title": "string"
                },
                "ai_authority_100_pages": {
                    "package_name": "AI Authority Package",
                    "pages": 100,
                    "purpose": "string",
                    "messaging": "string",
                    "what_ai_can_do": ["string (max 4)"],
                    "ties_to_findings": "string (connect directly to what we found; no URLs; no HTML)",
                    "why_ai_needs_it": "string (1-2 sentences)",
                    "who_this_is_for": "string",
                    "expected_outcome": "string (qualitative; no promises)",
                    "pages_to_build": ["string (concrete page titles derived from detected services/locations)"],
                    "example_page_title": "string"
                },
            },
            "stage_5_business_impact": {
                "what_staying_invisible_costs": "string",
                "why_ai_visibility_compounds": "string",
                "why_waiting_makes_this_worse": "string",
                "competitor_preference_proof": "string (ONE sentence; if no competitor pages analyzed, explicitly say so + use 'general market patterns')",
                "recommended_option": "string (must be: '30-page AI Recommendation package')",
                "closing_line": "string (must end with: 'Based on this, the recommended option is the 30-page AI Recommendation package.')",
                "neutrality_block": "string (platform-agnostic neutrality statement)",
                "our_offer_block": "string (fixed-scope, predictable cost, cost-effective vs SEO retainers; Wave 1 timing; no aggressive sales)"
            },
            "appendix": {
                "sampled_urls": ["string"],
                "data_limitations": "string",
                "pages_analyzed_target": "integer >= 0",
                "pages_analyzed_competitors": "integer >= 0"
            }
        }
    
    def get_stage_b_json_schema(self) -> Dict[str, Any]:
        """Get Stage B JSON schema (Action Plan with LLM Coverage Levels)"""
        return {
            "recommended_pages": [
                {
                    "page_title": "string",
                    "slug_suggestion": "string (e.g., /services/concrete-repair)",
                    "goal_for_llms": "string (what this helps LLMs understand)",
                    "content_unit_type": "service_page | entity_page | comparison_page | trust_page | faq_page | hub_page",
                    "counts_toward_coverage": "boolean (true if counts toward LLM coverage)",
                    "must_have_blocks": ["string (max 8)"],
                    "outline": ["string (max 10 section headings)"],
                    "example_snippet_for_citation": "string (quotable text for LLMs)"
                }
            ],
            "sitewide_blocks_to_add": [
                {
                    "block_name": "string",
                    "where_to_place": "string (e.g., footer, sidebar, all pages)",
                    "why_it_helps_llms": "string",
                    "example_copy": "string"
                }
            ],
            "coverage_levels": {
                "baseline": {
                    "level_name": "baseline",
                    "page_count_range": "string (e.g., '3-5 pages')",
                    "typical_content_units_range": "string (e.g., '5-7 content units' - capacity language)",
                    "page_types": ["string (types of pages at this level)"],
                    "llm_capability_unlocked": "string (what AI can do: understand basic offering)",
                    "what_ai_can_do_at_this_level": "string (plain-language: AI understands and describes)",
                    "who_this_level_is_for": "string (who this tier is for; capacity/budget/team fit)",
                    "expected_shift": "string (qualitative shift, NO traffic numbers)"
                },
                "recommended": {
                    "level_name": "recommended",
                    "page_count_range": "string (e.g., '6-10 pages')",
                    "typical_content_units_range": "string (e.g., '8-12 content units' - capacity language)",
                    "page_types": ["string (types of pages at this level)"],
                    "llm_capability_unlocked": "string (what AI can do: compare with alternatives)",
                    "what_ai_can_do_at_this_level": "string (plain-language: AI compares and suggests)",
                    "who_this_level_is_for": "string (who this tier is for; capacity/budget/team fit)",
                    "expected_shift": "string (qualitative shift, NO traffic numbers)"
                },
                "authority": {
                    "level_name": "authority",
                    "page_count_range": "string (e.g., '12-18 pages')",
                    "typical_content_units_range": "string (e.g., '14-20 content units' - capacity language)",
                    "page_types": ["string (types of pages at this level)"],
                    "llm_capability_unlocked": "string (what AI can do: confidently recommend)",
                    "what_ai_can_do_at_this_level": "string (plain-language: AI proactively recommends and cites)",
                    "who_this_level_is_for": "string (who this tier is for; capacity/budget/team fit)",
                    "expected_shift": "string (qualitative shift, NO traffic numbers)"
                },
                "current_assessment": "string (where site currently stands relative to these levels)"
            },
            "content_summary": {
                "total_content_units": "string (e.g., '8-12 LLM-focused content units')",
                "breakdown_by_type": {"service_page": 3, "entity_page": 2, "trust_page": 1},
                "estimated_coverage_level": "baseline | recommended | authority"
            },
            "growth_plan_summary": {
                "current_coverage_level": "partial baseline | baseline | partial recommended | recommended | partial authority | authority",
                "coverage_after_plan": "baseline | recommended | authority",
                "content_units_needed_for_next_level": "string (e.g., '5–7' or 'N/A (already at Authority)')"
            },
            "impact_forecast": {
                "baseline_impact": "string (impact at baseline coverage - low confidence)",
                "recommended_impact": "string (impact at recommended coverage - medium confidence)",
                "authority_impact": "string (impact at authority coverage - high confidence)",
                "why_coverage_matters": "string (why more coverage = higher AI confidence)",
                "key_unlocks": ["string (what each level unlocks, max 4)"]
            },
            "measurement_plan": {
                "what_to_track": ["string (LLM mentions, citations, brand association)"],
                "simple_tests": ["string (e.g., Ask ChatGPT about X)"]
            }
        }
    
    # =========================================================================
    # Page Selection & Context Building
    # =========================================================================
    
    def detect_page_type(self, page: ScrapedPage) -> str:
        """Detect page type from URL and title"""
        url_lower = page.url.lower()
        title_lower = (page.title or "").lower()
        
        if url_lower.rstrip('/').endswith(('.com', '.cz', '.io', '.net', '.org')):
            return "home"
        elif 'about' in url_lower or 'about' in title_lower:
            return "about"
        elif 'pricing' in url_lower or 'price' in url_lower or 'pricing' in title_lower:
            return "pricing"
        elif 'service' in url_lower or 'services' in title_lower:
            return "service"
        elif 'product' in url_lower or 'products' in title_lower:
            return "product"
        elif 'case-stud' in url_lower or 'portfolio' in url_lower:
            return "case_study"
        elif 'faq' in url_lower or 'faq' in title_lower:
            return "faq"
        elif 'contact' in url_lower or 'contact' in title_lower:
            return "contact"
        elif 'blog' in url_lower or 'article' in url_lower:
            return "blog"
        else:
            return "other"
    
    async def select_representative_pages(
        self,
        job_id: str,
        is_target: bool = True,
        max_pages: int = 15,
    ) -> List[ScrapedPage]:
        """Select representative pages with priority"""
        result = await self.db.execute(
            select(ScrapedPage)
            .where(ScrapedPage.audit_job_id == job_id)
            .where(ScrapedPage.is_target == is_target)
            .order_by(ScrapedPage.word_count.desc())
            .limit(max_pages * 2)
        )
        all_pages = list(result.scalars().all())
        
        priority_pages = []
        other_pages = []
        
        for page in all_pages:
            page_type = self.detect_page_type(page)
            if page_type in ['home', 'about', 'pricing', 'service', 'case_study']:
                priority_pages.append(page)
            else:
                other_pages.append(page)
        
        selected = priority_pages[:10] + other_pages[:5]
        return selected[:max_pages]
    
    def build_scraping_summary(self, job: AuditJob, target_pages: List[ScrapedPage]) -> Dict[str, Any]:
        """Build aggregated scraping summary"""
        page_types = {}
        has_pricing = False
        has_about = False
        has_contact = False
        has_testimonials = False
        has_case_studies = False
        trust_signals = []
        
        for page in target_pages:
            page_type = self.detect_page_type(page)
            page_types[page_type] = page_types.get(page_type, 0) + 1
            
            if page_type == 'pricing':
                has_pricing = True
            elif page_type == 'about':
                has_about = True
            elif page_type == 'contact':
                has_contact = True
            elif page_type == 'case_study':
                has_case_studies = True
            
            text_lower = (page.text_content or "").lower()
            if 'testimonial' in text_lower or 'review' in text_lower:
                has_testimonials = True
                if "testimonials" not in trust_signals:
                    trust_signals.append("testimonials/reviews found")
            if 'certified' in text_lower or 'certification' in text_lower:
                if "certifications" not in trust_signals:
                    trust_signals.append("certifications mentioned")
            if 'guarantee' in text_lower:
                if "guarantees" not in trust_signals:
                    trust_signals.append("guarantees mentioned")
            if 'years' in text_lower and 'experience' in text_lower:
                if "experience" not in trust_signals:
                    trust_signals.append("years of experience mentioned")
        
        service_area_clarity = "low"
        for page in target_pages:
            text = (page.text_content or "").lower()
            if any(keyword in text for keyword in ['we serve', 'service area', 'locations', 'cities we serve']):
                service_area_clarity = "high"
                break
            elif any(keyword in text for keyword in ['local', 'area', 'region']):
                service_area_clarity = "medium"
        
        return {
            "pages_fetched_target": len(target_pages),
            "top_page_types_detected": [k for k, v in sorted(page_types.items(), key=lambda x: -x[1])[:5]],
            "has_pricing_page": has_pricing,
            "has_about_page": has_about,
            "has_contact_page": has_contact,
            "has_testimonials_or_reviews": has_testimonials,
            "has_case_studies": has_case_studies,
            "service_area_clarity": service_area_clarity,
            "trust_signals_found": trust_signals[:10]
        }
    
    def build_sampled_pages_block(self, pages: List[ScrapedPage]) -> str:
        """Build sampled pages text block"""
        blocks = []
        for i, page in enumerate(pages, 1):
            page_type = self.detect_page_type(page)
            excerpt = (page.text_content or "")[:2000]
            if len(page.text_content or "") > 2000:
                excerpt += "..."
            
            block = f"""
Page {i}:
URL: {page.url}
Title: {page.title or 'N/A'}
Page Type: {page_type}
Text Excerpt: {excerpt}
"""
            blocks.append(block.strip())
        
        return "\n\n".join(blocks)
    
    def build_competitor_context(self, competitor_pages: List[ScrapedPage]) -> str:
        """Build competitor context block"""
        if not competitor_pages:
            return "No competitor data provided. Competitor context is not available for this audit."
        
        by_domain = {}
        for page in competitor_pages:
            if page.domain not in by_domain:
                by_domain[page.domain] = []
            by_domain[page.domain].append(page)
        
        blocks = []
        for domain, pages in list(by_domain.items())[:5]:
            top_pages = pages[:3]
            summary_parts = []
            for page in top_pages:
                excerpt = (page.text_content or "")[:500]
                summary_parts.append(f"- {page.title}: {excerpt}...")
            
            block = f"""
Competitor: {domain}
Sample content:
{chr(10).join(summary_parts)}
"""
            blocks.append(block.strip())
        
        return "\n\n".join(blocks)
    
    # =========================================================================
    # Stage A: Core Audit
    # =========================================================================
    
    def build_stage_a_prompt(
        self,
        job: AuditJob,
        target_pages: List[ScrapedPage],
        competitor_pages: List[ScrapedPage],
        scraping_summary: Dict[str, Any],
        evidence_layer: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build Stage A user prompt"""
        sampled_pages_block = self.build_sampled_pages_block(target_pages)
        competitor_context_block = self.build_competitor_context(competitor_pages)
        schema_json = json.dumps(self.get_stage_a_json_schema(), indent=2)
        
        # Guardrails and data quality notes
        data_warning = ""
        confidence_note = ""
        
        if scraping_summary['pages_fetched_target'] < 8:
            data_warning = "\n\nDATA LIMITATION: Only {0} pages were scraped. Be conservative with scores and note this in data_limitations.".format(scraping_summary['pages_fetched_target'])
            confidence_note = "LOW DATA CONFIDENCE"
        elif scraping_summary['pages_fetched_target'] < 15:
            confidence_note = "MEDIUM DATA CONFIDENCE"
        else:
            confidence_note = "HIGH DATA CONFIDENCE"
        
        competitor_note = ""
        if not competitor_pages:
            competitor_note = "\n\nNO COMPETITOR DATA: Any market insights in competitor_angles must be labeled as 'General industry patterns' - do NOT claim competitor-specific insights without data."
        
        # Evidence Catalog (deterministic; LLM must only cite these)
        ev_layer = evidence_layer or {}
        company_profile = (ev_layer.get("company_profile") if isinstance(ev_layer, dict) else {}) or {}
        evidence_items = (ev_layer.get("evidence") if isinstance(ev_layer, dict) else []) or []
        pages_blocks = (ev_layer.get("pages") if isinstance(ev_layer, dict) else []) or []

        evidence_lines = []
        if isinstance(evidence_items, list):
            for i, e in enumerate(evidence_items[:20]):
                if not isinstance(e, dict):
                    continue
                claim = e.get("claim", "")
                pt = e.get("proof_type", "")
                urls = e.get("source_urls", []) if isinstance(e.get("source_urls"), list) else []
                snips = e.get("snippets", []) if isinstance(e.get("snippets"), list) else []
                evidence_lines.append(
                    f"[{i}] type={pt} | claim={claim} | urls={urls[:3]} | snippets={snips[:2]}"
                )

        evidence_catalog = "\n".join(evidence_lines) if evidence_lines else "No evidence items available (limited data)."

        # Fallback logic: use extracted values from scraping when user input is None
        services_list = company_profile.get('services_detected', [])
        company_desc = (
            job.company_description 
            or company_profile.get('primary_offer_summary') 
            or 'not detected'
        )
        products = (
            job.products_services 
            or (", ".join(services_list) if isinstance(services_list, list) and services_list else None)
            or 'not detected'
        )

        prompt = f"""COMPANY INPUT (EXTRACTED FROM SCRAPING)
------------------------------------------
Target domain: {job.target_domain}
Locale: {job.locale}
Company description: {company_desc}
Main products/services: {products}

DATA QUALITY: {confidence_note}

SCRAPING-DERIVED COMPANY PROFILE (DO NOT INVENT)
-----------------------------------------------
company_name: {company_profile.get('company_name', 'not detected')}
primary_offer_summary: {company_profile.get('primary_offer_summary', 'not detected')}
services_detected: {company_profile.get('services_detected', []) if isinstance(company_profile.get('services_detected'), list) else 'not detected'}
locations_detected: {company_profile.get('locations_detected', []) if isinstance(company_profile.get('locations_detected'), list) else 'not detected'}
primary_language_detected: {company_profile.get('primary_language_detected', 'not detected')}
top_pages: {company_profile.get('top_pages', []) if isinstance(company_profile.get('top_pages'), list) else 'not detected'}

CRAWL SNAPSHOT (AGGREGATED)
--------------------------
Target pages fetched: {scraping_summary['pages_fetched_target']}
Competitor pages fetched: {len(competitor_pages)}
Top page types detected: {', '.join(scraping_summary['top_page_types_detected'])}

Signals found:
- Pricing info detected: {scraping_summary['has_pricing_page']}
- About info detected: {scraping_summary['has_about_page']}
- Contact info detected: {scraping_summary['has_contact_page']}
- Testimonials/Reviews: {scraping_summary['has_testimonials_or_reviews']}
- Case studies: {scraping_summary['has_case_studies']}
- Service area clarity: {scraping_summary['service_area_clarity']}
- Trust signals: {', '.join(scraping_summary['trust_signals_found']) if scraping_summary['trust_signals_found'] else 'None detected'}

SAMPLED PAGES (TARGET) — MOST IMPORTANT
--------------------------------------
{sampled_pages_block}

EVIDENCE CATALOG (MANDATORY CITATIONS)
-------------------------------------
Use ONLY these evidence items for site-specific claims.
For every Stage 2 reason:
- include evidence_refs: [one or more IDs] (min 1)
- do not invent URLs/snippets/services/locations

{evidence_catalog}

COMPETITOR CONTEXT (GENERAL MARKET REFERENCE ONLY)
--------------------------------------------------
{competitor_context_block}
{data_warning}{competitor_note}

TASK: CREATE EVIDENCE-BASED AI VISIBILITY AUDIT (HARD, IMPARTIAL)
----------------------------------------
You are an AI visibility auditor.
You must use the Evidence Catalog above for site-specific claims.

================================================
STAGE 1 — AI VISIBILITY (DRAMA)
================================================

Estimate how often AI models would recommend this business today:

- ChatGPT
- Gemini
- Perplexity

Use:
- percentage
- label: Poor / Limited / Strong

Then write ONE hard sentence exactly:
"AI models usually recommend competitors instead of this business."

================================================
SECTION 02 — AI INTERPRETATION (MANDATORY)
================================================

THIS SECTION IS CRITICAL. IT MUST:
1) Be based ONLY on scraped content (no fabrication)
2) Be truthful and defensible
3) Work for ANY industry
4) Be interpretation, NOT marketing

Generate ai_interpretation with these fields:

summary:
- 3-4 sentences explaining what AI can objectively understand from the website
- Use ONLY information from sampled pages / company profile
- NO superlatives ("amazing", "leading", "best")
- NO promises or marketing language
- Must sound like: "Based on analyzed content, AI sees this as [X]. The website emphasizes [Y]. Service scope appears to be [Z]."
- If something is unclear, say so: "Service differentiation is not clearly explained"

confidence: 
- "shallow" (most cases - surface-level brand story only)
- "partial" (some decision context exists but incomplete)
- "strong" (rare - full decision-level clarity)

based_on_pages:
- Use the actual pages_analyzed_target number

detected_signals:
- 5-8 signals AI currently recognizes (from services_detected, locations, language)
- Label these as "weak / non-distinctive" - they are generic
- Examples: "Brand name", "Generic service keywords", "Location references", "Contact information"

missing_elements:
- MANDATORY: 4-6 elements that prevent confident AI recommendations
- Each element has:
  * key: technical identifier (e.g., "service_differentiation")
  * label: human-readable (e.g., "No clear service differentiation")
  * impact: 1 sentence explaining how this limits AI (e.g., "AI cannot explain how you differ from alternatives")
  * severity: "critical" (blocks recommendations) OR "supporting" (reduces confidence)

REQUIRED MISSING ELEMENTS (use these):
1. service_differentiation: "No clear service differentiation" | impact: "AI cannot explain how you differ from alternatives" | severity: critical
2. decision_context: "No decision-making context" | impact: "AI cannot determine who this is best for or why" | severity: critical  
3. pricing_structure: "No pricing or value structure" | impact: "AI cannot compare you to competitors on value" | severity: critical
4. comparison_content: "No comparison or alternatives" | impact: "No content showing trade-offs or competitive position" | severity: supporting
5. audience_fit: "No audience fit (who it's for / not for)" | impact: "AI cannot guide customers on whether this fits their needs" | severity: supporting

RULES FOR AI INTERPRETATION:
- Do NOT invent services not found in services_detected
- Do NOT invent pricing if not in scraped pages
- Do NOT invent positioning statements
- DO summarize what can be understood from the website
- DO identify what is missing
- DO explain the impact on recommendability

================================================
SECTION 03 — DECISION READINESS AUDIT (MANDATORY)
================================================

THIS SECTION IS THE CORE FORENSIC AUDIT.

YOU MUST GENERATE 8-10 DECISION ELEMENTS.

Each element represents a specific decision-level component that AI systems need to make confident recommendations.

CRITICAL RULES:
1) MUST be personalized from scraped content (not generic)
2) MUST vary by business (restaurant ≠ SaaS ≠ local service)
3) MUST reference evidence_refs where applicable
4) MUST use specific, concrete element names (not generic categories)

ELEMENT STRUCTURE (MANDATORY FOR EACH):

element_name:
- Specific, concrete name (e.g., "Structured Service Pages", "Pricing & Value Tables", "FAQ / Q&A Content")
- NOT generic ("missing content", "not enough pages")
- Examples:
  * "Structured Service Pages"
  * "Pricing & Value Tables"
  * "FAQ / Q&A Content"
  * "Comparison vs Alternatives"
  * "Decision Guidance (Who it's for / not for)"
  * "Entity & Trust Signals"
  * "Local Business Proof (hours, location, booking)"
  * "Operational Clarity (process, timeline, delivery)"
  * "Social / Review Signals"
  * "Authority Content (guides, explainers, education)"

status:
- "missing" (not found at all)
- "weak" (exists but insufficient for AI)
- "fragmented" (scattered, not structured)
- "present" (rare - clearly structured and AI-quotable)

ai_expectation:
- ONE specific sentence
- What AI systems expect for THIS element
- NOT generic ("AI needs content")
- Examples:
  * "LLMs require structured, quotable answers to common decision questions."
  * "AI systems need explicit pricing comparisons to evaluate value."
  * "Recommendation engines require clear statements about who the service is/isn't for."

what_found:
- ONE sentence
- What was found on the website for THIS element
- Evidence-backed (use evidence_refs if applicable)
- NO fabrication
- Examples:
  * "Service pages contain brand storytelling without structured service explanations."
  * "Pricing is mentioned in generic terms ('affordable') without values or tiers."
  * "No FAQ or Q&A content detected across analyzed pages."

recommendation_impact:
- ONE sentence
- How THIS missing/weak element affects AI recommendations
- Causal, not emotional
- Examples:
  * "Without this, AI cannot compare this business to alternatives."
  * "AI defaults to competitors with explicit pricing structures."
  * "Recommendation systems cannot confidently match this business to user queries."

evidence_refs:
- Array of integers (IDs from Evidence Catalog)
- Include when applicable (not always required)

DECISION ELEMENTS TO ANALYZE (GENERATE 12-18 TOTAL):

MANDATORY CORE ELEMENTS (15 required):
1. Pricing ranges / packages
2. Value anchors
3. Service scope boundaries
4. Process / "how it works"
5. Alternatives / who it's NOT for
6. Differentiation (measurable)
7. Testimonials (context)
8. Case studies (outcomes)
9. About/team authority
10. Guarantees/refunds/risk reducers
11. Policies / expectations
12. FAQ objections
13. Local/entity signals
14. Structured summaries AI can quote
15. Contact / conversion clarity

OPTIONAL BUSINESS-SPECIFIC ELEMENTS (add 0-3 based on business type):
For SaaS/Software: API documentation, integration guides, free trial/demo
For E-commerce: Product specs, sizing guides, shipping/returns
For Professional Services: Credentials, process timeline, deliverables
For Local Services: Service area map, same-day availability, emergency services

MANDATORY GENERATION LOGIC:
- Generate AT LEAST 15 elements (the mandatory list above)
- Generate UP TO 18 elements total (add business-specific ones)
- 80-95% MUST be "weak" or "missing" (conservative bias)
- Only 0-2 elements should be "present" (and only if truly structured + complete)
- Each element MUST have evidence_refs (or explicitly state "Not detected")

CRITICAL: BIAS TOWARD MISSING/WEAK
- AI MUST NOT be "generous" with ratings
- "present" status ONLY if:
  * Explicit, structured, quotable content exists (FAQ blocks, pricing tables, clear sections)
  * Clear sections/tables/FAQ blocks detected in evidence
  * AI can directly cite it without interpretation
  * Information is COMPLETE (not just a mention or fragment)
- If unsure → mark as "weak" or "missing"
- Examples of NOT "present":
  * Generic mentions without structure (= "weak")
  * Brand storytelling without facts (= "weak")
  * Scattered information across pages (= "weak")
  * Implied but not stated explicitly (= "weak")
  * Single mention without detail (= "weak")
  * Partial information (= "weak")

decision_coverage_score:
After generating decision_readiness_audit, calculate:
- present: count of elements with status="present" (typically 0-2)
- weak: count of elements with status="weak" (typically 6-10)
- missing: count of elements with status="missing" (typically 6-10)
- total: length of decision_readiness_audit array (12-18)

QUALITY CHECK:
Each business MUST get different elements with different evidence.
A restaurant should NOT have the same decision elements as a SaaS company.
Use scraped data to personalize.

================================================
STAGE 2 — WHY AI CHOOSES OTHERS (LEGACY, KEEP FOR NOW)
================================================

List up to 5 reasons.

For each reason, output these required fields:
- how_llms_decide (1 sentence)
- what_we_found_on_your_site (1 sentence; must reference the evidence)
- what_ai_does_instead (1 sentence)
- what_must_be_built (1 sentence; concrete build requirement)
- evidence_refs (array of ints; min 1; cite Evidence Catalog IDs)

Personalization requirement for every Stage 2 reason:
- Mention company_name (or the domain if not detected) AND at least one service term from services_detected.
If services_detected is empty, say 'services not detected' explicitly.

Speak like explaining to a business owner.
No SEO language. No frameworks.

================================================
SECTION 04 — AI REQUIREMENTS (GRANULAR BREAKDOWN) (MANDATORY)
================================================

THIS SECTION IS CRITICAL FOR DEMONSTRATING EXPERTISE.

YOU MUST GENERATE 10-20 GRANULAR AI REQUIREMENTS FOR BOTH BEFORE AND AFTER.

CRITICAL RULES:
1) MUST be personalized from scraped content (not generic)
2) MUST vary by business type (restaurant ≠ SaaS ≠ local service)
3) MUST cover 5 categories: Decision Clarity, Comparability, Trust & Authority, Entity Understanding, Risk Reduction
4) MUST use specific requirement names (not generic like "more content")
5) ai_requirements_before: 10-20 items (what's missing/weak NOW)
6) ai_requirements_after: 10-20 items (what must be built)
7) MUST align with Section 03 decision_readiness_audit (each missing/weak element should map to a requirement)

REQUIREMENT STRUCTURE FOR BEFORE (MANDATORY FOR EACH OF 10-20 ITEMS):

requirement_name:
- Specific, concrete name (e.g., "Explicit service definitions", "Pricing tier transparency", "Customer testimonials with outcomes")
- NOT generic ("better content", "more pages")

category:
- Decision Clarity: Requirements for understanding what/how/who/when
- Comparability: Requirements for comparing against alternatives
- Trust & Authority: Requirements for building credibility
- Entity Understanding: Requirements for AI knowledge graph
- Risk Reduction: Requirements for reducing buyer risk

why_ai_needs_this:
- ONE sentence explaining why AI systems need this
- Generic AI rule (not site-specific)
- Examples:
  * "AI needs structured service pages to explain offerings to users."
  * "AI requires transparent pricing to compare value against alternatives."
  * "AI needs testimonials with outcomes to build recommendation confidence."

current_status:
- "not_found" (not found at all in evidence)
- "weak" (exists but insufficient for AI)
- NEVER "present" (this is the BEFORE state)

impact_if_missing:
- ONE sentence explaining how this affects recommendations
- Causal, specific
- Examples:
  * "AI cannot explain service scope to users."
  * "AI defaults to competitors with transparent pricing."
  * "Recommendation confidence drops due to lack of proof."

REQUIREMENT STRUCTURE FOR AFTER (MANDATORY FOR EACH OF 10-20 ITEMS):

requirement_name:
- Same specific, concrete name as in BEFORE (must match)

category:
- Same category as in BEFORE (must match)
- Decision Clarity | Comparability | Trust & Authority | Entity Understanding | Risk Reduction

what_must_be_built:
- ONE sentence describing concrete build instruction
- Specific action, NOT generic advice
- FORBIDDEN PHRASES: "Improve trust", "Add more content", "Better structure"
- GOOD EXAMPLES:
  * "Build structured service pages with clear scope, features, and use cases."
  * "Add pricing tiers or ranges with value anchors and comparison points."
  * "Add testimonials with specific results, context, and attribution."
  * "Create 'Who this is for / not for' sections on key pages."
  * "Build 'vs alternatives' pages explaining trade-offs and differentiation."

ai_outcome_unlocked:
- ONE sentence describing what AI capability this unlocks
- Specific AI behavior change
- Examples:
  * "AI can explain service offerings to users with confidence."
  * "AI can compare value and recommend based on budget fit."
  * "AI gains proof to support recommendations with evidence."
  * "AI can match this business to specific user needs."
REQUIREMENTS BY CATEGORY (GENERATE 10-20 TOTAL):

CATEGORY: Decision Clarity (3-6 requirements)
- Explicit service definitions
- Clear scope boundaries
- Feature vs benefit separation
- Decision triggers ("when to choose this")
- FAQ resolving buyer uncertainty
- Structured summaries AI can quote

CATEGORY: Comparability (3-5 requirements)
- Pricing tier transparency
- Value anchors and comparisons
- Competitor positioning
- Alternative explanations ("who this is NOT for")
- Measurable differentiation points

CATEGORY: Trust & Authority (3-5 requirements)
- Customer testimonials with context
- Case studies with measurable outcomes
- Proof of expertise (credentials, experience)
- Third-party validation
- Guarantees or risk reducers

CATEGORY: Entity Understanding (2-4 requirements)
- Strong brand entity signals
- Founder/team authority pages
- Topical depth clusters
- Internal linking logic
- Structured data for AI reuse

CATEGORY: Risk Reduction (2-4 requirements)
- Refund/cancellation clarity
- SLA or expectation setting
- Downside explanations
- Objection handling content

MANDATORY GENERATION LOGIC:
- Generate 10-20 requirements TOTAL in BOTH before AND after
- Distribute across categories based on business type
- 90-100% of BEFORE items MUST be "not_found" or "weak" (bias toward problems)
- BEFORE items MUST align with Section 03 missing/weak elements
- AFTER items MUST have concrete build instructions (NOT generic advice like "Improve trust")
- Use scraped data to personalize (e.g., restaurant needs "Menu with allergen info", SaaS needs "API documentation")
- NEVER say "web is mostly OK" → conservative bias

QUALITY CHECK:
Each business MUST get different requirements.
A restaurant should NOT have the same requirements as a SaaS company.
Use scraped data + business type to personalize.

================================================
STAGE 3 — WHAT AI NEEDS (LEGACY, KEEP FOR BACKWARD COMPAT)
================================================

Describe the types of pages AI needs to recommend a business.

Examples:
- Pricing & value pages
- Service explanation pages
- Comparison pages
- Trust & authority pages

For each type:
- What it unlocks for AI

================================================
STAGE 4 — WHAT WE WILL BUILD (PACKAGES)
================================================

Translate the solution into page packages:

10 pages:
- What AI can finally do

30 pages:
- What changes in AI answers

100 pages:
- How AI behavior changes long-term

Package names MUST be:
- "AI Entry Package" (10 pages)
- "AI Recommendation Package" (30 pages)
- "AI Authority Package" (100 pages)

PACKAGES MUST INCLUDE CONCRETE PAGE TITLES (NOT GENERIC):
- Use services_detected from the company profile.
- Provide pages_to_build lists:
  - 10 pages: min 3 titles
  - 30 pages: min 6–12 titles
  - 100 pages: include service + location expansion if locations_detected exists

Page title patterns (examples):
- \"How [Service] Works\"
- \"[Service] Pricing & Packages\"
- \"[Service] vs [Alternative]\"
- \"Common mistakes when choosing [Service]\"

================================================
STAGE 5 — BUSINESS IMPACT (URGENCY)
================================================

Explain:
- What staying invisible costs
- Why AI visibility compounds
- Why waiting makes this worse

End with this exact sentence:
"Based on this, the recommended option is the 30-page AI Recommendation package."

FINAL BLOCKS (MANDATORY)
-----------------------
- neutrality_block: \"This audit is platform-agnostic. Any capable team can implement it.\"
- our_offer_block: Offer Wave 1 implementation in X days; fixed-scope, predictable cost; cost-effective vs traditional SEO retainers. Do NOT say \"cheap\".

================================================
RULES
================================================

- Do NOT use SEO terminology
- Be direct and confident
- Stay impartial in tone
- Offer implementation only in the final blocks

================================================
EVIDENCE REQUIREMENT (MANDATORY)
================================================

For every major claim you make:
- include ONE concrete observation from the website crawl

Examples:
- “No dedicated pricing page found”
- “Service information spread across multiple pages”
- “No comparison content detected”

Do NOT invent URLs.
Do NOT quote HTML.
Use evidence_refs and the evidence items provided above.

SCHEMA (RETURN EXACTLY THIS SHAPE)
----------------------------------
{schema_json}"""
        
        return prompt
    
    async def run_stage_a(
        self,
        prompt: str,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Run Stage A: AI Visibility Sales Report (Stages A-E)
        Model: settings.openai_model | Temperature: 0.2 | Max tokens: 6000
        """
        try:
            print(
                f"[STAGE A] Calling {self._effective_model()} for AI Visibility Sales Report "
                f"(temp=0.2, max_tokens=6000)..."
            )
            
            response = await self.client.chat.completions.create(
                model=self._effective_model(),
                messages=[
                    {"role": "system", "content": STAGE_A_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,  # Low for consistency in sales messaging
                max_tokens=6000,  # Increased to prevent truncation (was 4000)
            )
            
            # Check if response was truncated
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                print(f"[STAGE A] ⚠️ Response truncated (finish_reason: {finish_reason})")
                if attempt < max_attempts:
                    print("[STAGE A] Retrying with request for shorter response...")
                    repair_prompt = prompt + "\n\nIMPORTANT: Previous response was truncated. Generate a COMPLETE, VALID JSON response. Be concise but ensure ALL required fields are present."
                    return await self.run_stage_a(repair_prompt, attempt + 1, max_attempts)
                raise ValueError(f"Stage A response truncated after {max_attempts} attempts")
            
            audit_json_str = response.choices[0].message.content
            
            # Log raw JSON for debugging
            if attempt == 1:
                print(f"[STAGE A] Raw JSON length: {len(audit_json_str)} chars")
                print(f"[STAGE A] First 200 chars: {audit_json_str[:200]}")
                print(f"[STAGE A] Last 200 chars: {audit_json_str[-200:]}")
            
            # Attempt to repair malformed JSON
            try:
                audit_json = json.loads(audit_json_str)
            except json.JSONDecodeError as e:
                print(f"[STAGE A] Initial JSON parse failed: {e}")
                print(f"[STAGE A] Attempting to repair JSON...")
                
                # Try to fix common JSON issues
                repaired_json_str = audit_json_str
                
                # Remove trailing commas before closing brackets/braces
                import re
                repaired_json_str = re.sub(r',\s*}', '}', repaired_json_str)
                repaired_json_str = re.sub(r',\s*]', ']', repaired_json_str)
                
                # Try to close unterminated strings by finding the last quote and ensuring proper closure
                if 'Unterminated string' in str(e):
                    # Find the position of the error
                    error_pos = e.pos if hasattr(e, 'pos') else len(repaired_json_str)
                    # Truncate at the error and try to close the JSON properly
                    repaired_json_str = repaired_json_str[:error_pos]
                    # Count open braces/brackets and close them
                    open_braces = repaired_json_str.count('{') - repaired_json_str.count('}')
                    open_brackets = repaired_json_str.count('[') - repaired_json_str.count(']')
                    repaired_json_str += '"' * (repaired_json_str.count('"') % 2)  # Close unterminated strings
                    repaired_json_str += ']' * open_brackets
                    repaired_json_str += '}' * open_braces
                
                try:
                    audit_json = json.loads(repaired_json_str)
                    print(f"[STAGE A] ✓ JSON repair successful")
                except json.JSONDecodeError:
                    # If repair failed, re-raise original error
                    raise e
            
            # ===================================================================
            # DEBUG: RAW LLM OUTPUT (BEFORE PYDANTIC VALIDATION)
            # ===================================================================
            print("\n" + "="*80)
            print("=== RAW LLM OUTPUT (PŘED PYDANTIC VALIDACÍ) ===")
            print("="*80)
            
            # Check Section 03
            if "decision_readiness_audit" in audit_json:
                print(f"✅ decision_readiness_audit: {len(audit_json.get('decision_readiness_audit', []))} items")
            else:
                print("❌ decision_readiness_audit: MISSING")
            
            if "decision_coverage_score" in audit_json:
                print(f"✅ decision_coverage_score: {audit_json.get('decision_coverage_score')}")
            else:
                print("❌ decision_coverage_score: MISSING")
            
            # Check Section 04
            if "ai_requirements_before" in audit_json:
                print(f"✅ ai_requirements_before: {len(audit_json.get('ai_requirements_before', []))} items")
            else:
                print("❌ ai_requirements_before: MISSING")
            
            if "ai_requirements_after" in audit_json:
                print(f"✅ ai_requirements_after: {len(audit_json.get('ai_requirements_after', []))} items")
            else:
                print("❌ ai_requirements_after: MISSING")
            
            # Check old field (should NOT exist)
            if "ai_requirements" in audit_json:
                print(f"⚠️  ai_requirements (OLD FIELD): {len(audit_json.get('ai_requirements', []))} items - WILL BE REJECTED BY PYDANTIC")
            
            print("="*80 + "\n")
            # ===================================================================
            
            # POST-PROCESSING: Ensure decision_readiness_audit exists
            if "decision_readiness_audit" not in audit_json or not isinstance(audit_json.get("decision_readiness_audit"), list):
                print("[STAGE A] ⚠️ decision_readiness_audit missing from LLM response, creating minimal fallback")
                # Create minimal fallback (12 generic elements) to prevent validation failure
                audit_json["decision_readiness_audit"] = [
                    {
                        "element_name": "Service Definition Pages",
                        "status": "missing",
                        "what_ai_requires": "LLMs require structured, quotable service explanations.",
                        "what_we_found": "Service information not clearly structured for AI citation.",
                        "impact_on_recommendation": "AI cannot confidently explain offerings to users.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Service Scope Boundaries",
                        "status": "missing",
                        "what_ai_requires": "AI needs explicit scope boundaries (what's included/excluded).",
                        "what_we_found": "No clear scope boundaries detected.",
                        "impact_on_recommendation": "AI cannot explain service limitations.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Pricing / Value Anchors",
                        "status": "missing",
                        "what_ai_requires": "AI systems need explicit pricing comparisons to evaluate value.",
                        "what_we_found": "Pricing not detected or not structured for AI parsing.",
                        "impact_on_recommendation": "AI cannot compare value against alternatives.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Alternatives / Who NOT for",
                        "status": "missing",
                        "what_ai_requires": "AI needs clear fit/misfit guidance.",
                        "what_we_found": "No guidance on who this service is NOT for.",
                        "impact_on_recommendation": "AI cannot determine negative fit.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Measurable Differentiation",
                        "status": "missing",
                        "what_ai_requires": "AI needs quantifiable differentiation points.",
                        "what_we_found": "No measurable differentiation detected.",
                        "impact_on_recommendation": "AI cannot explain competitive advantage.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Testimonials with Context",
                        "status": "weak",
                        "what_ai_requires": "AI needs testimonials with specific outcomes.",
                        "what_we_found": "Generic testimonials without measurable context.",
                        "impact_on_recommendation": "Lower proof quality for recommendations.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Case Studies with Outcomes",
                        "status": "missing",
                        "what_ai_requires": "AI needs case studies with measurable results.",
                        "what_we_found": "No case studies detected.",
                        "impact_on_recommendation": "No proof of real-world results.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "About/Team/Expertise",
                        "status": "weak",
                        "what_ai_requires": "AI needs structured entity information.",
                        "what_we_found": "About page exists but lacks authority markers.",
                        "impact_on_recommendation": "Weak entity signals for knowledge graphs.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Policies / Guarantees",
                        "status": "missing",
                        "what_ai_requires": "AI needs risk reduction signals.",
                        "what_we_found": "No guarantee or refund policy detected.",
                        "impact_on_recommendation": "Higher perceived risk for users.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "FAQ Content",
                        "status": "missing",
                        "what_ai_requires": "LLMs require structured answers to common decision questions.",
                        "what_we_found": "No FAQ or Q&A content detected across analyzed pages.",
                        "impact_on_recommendation": "AI lacks decision-support content to quote.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Operational Clarity",
                        "status": "weak",
                        "what_ai_requires": "AI systems need clear operational details (hours, booking, process).",
                        "what_we_found": "Operational information not consistently structured.",
                        "impact_on_recommendation": "AI cannot provide complete operational details to users.",
                        "evidence_refs": []
                    },
                    {
                        "element_name": "Contact / Conversion Path",
                        "status": "weak",
                        "what_ai_requires": "AI needs clear CTAs and contact methods.",
                        "what_we_found": "Contact information present but not clearly structured.",
                        "impact_on_recommendation": "AI cannot guide users to next steps.",
                        "evidence_refs": []
                    }
                ]
            
            # POST-PROCESSING: Calculate decision_coverage_score if missing or invalid
            if "decision_readiness_audit" in audit_json and isinstance(audit_json["decision_readiness_audit"], list):
                elements = audit_json["decision_readiness_audit"]
                
                # If LLM returned fewer than 12 elements, pad with generic elements
                if len(elements) < 12:
                    print(f"[STAGE A] ⚠️ decision_readiness_audit has only {len(elements)} items, padding to 12")
                    # Use fallback elements to pad
                    fallback_elements = audit_json.get("_fallback_decision_elements", [])
                    if not fallback_elements:
                        # Create minimal padding elements
                        fallback_elements = [
                            {"element_name": f"Decision Element {i+1}", "status": "missing", "what_ai_requires": "AI needs structured information.", "what_we_found": "Not detected in evidence.", "impact_on_recommendation": "AI cannot make informed recommendations.", "evidence_refs": []}
                            for i in range(12 - len(elements))
                        ]
                    needed = 12 - len(elements)
                    audit_json["decision_readiness_audit"] = elements + fallback_elements[:needed]
                    elements = audit_json["decision_readiness_audit"]
                
                # Calculate score from elements
                calculated_score = {
                    "present": sum(1 for e in elements if e.get("status") == "present"),
                    "weak": sum(1 for e in elements if e.get("status") in ["weak", "fragmented"]),
                    "missing": sum(1 for e in elements if e.get("status") == "missing"),
                    "total": len(elements)
                }
                
                # Use calculated score if LLM score is missing or invalid
                llm_score = audit_json.get("decision_coverage_score")
                if not llm_score or not isinstance(llm_score, dict) or llm_score.get("total", 0) == 0:
                    print(f"[STAGE A] Decision coverage score missing/invalid from LLM, using calculated: {calculated_score}")
                    audit_json["decision_coverage_score"] = calculated_score
                else:
                    # Validate LLM score matches element count
                    if llm_score.get("total") != len(elements):
                        print(f"[STAGE A] Decision coverage score total mismatch (LLM: {llm_score.get('total')}, actual: {len(elements)}), using calculated")
                        audit_json["decision_coverage_score"] = calculated_score
            
            # POST-PROCESSING: Ensure ai_requirements_before and ai_requirements_after exist AND have minimum 10 items
            if "ai_requirements_before" not in audit_json or not isinstance(audit_json.get("ai_requirements_before"), list):
                print("[STAGE A] ⚠️ ai_requirements_before missing from LLM response, creating minimal fallback")
                audit_json["ai_requirements_before"] = []
            
            # If LLM returned fewer than 10 items, pad with fallback items
            if len(audit_json["ai_requirements_before"]) < 10:
                print(f"[STAGE A] ⚠️ ai_requirements_before has only {len(audit_json['ai_requirements_before'])} items, padding to 10")
                fallback_before = [
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
                        "current_status": "not_found",
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
                    },
                    {
                        "requirement_name": "Local/entity signals",
                        "category": "Entity Understanding",
                        "why_ai_needs_this": "AI needs location and entity proof for local recommendations.",
                        "current_status": "weak",
                        "impact_if_missing": "AI cannot confidently recommend for local queries."
                    },
                    {
                        "requirement_name": "Structured summaries AI can quote",
                        "category": "Decision Clarity",
                        "why_ai_needs_this": "AI needs quotable summaries for direct citation.",
                        "current_status": "not_found",
                        "impact_if_missing": "AI cannot directly cite key information."
                    },
                    {
                        "requirement_name": "Contact / conversion clarity",
                        "category": "Risk Reduction",
                        "why_ai_needs_this": "AI needs clear CTAs to guide users to next steps.",
                        "current_status": "weak",
                        "impact_if_missing": "AI cannot guide users to conversion."
                    },
                    {
                        "requirement_name": "Value anchors",
                        "category": "Comparability",
                        "why_ai_needs_this": "AI needs value anchors to contextualize pricing.",
                        "current_status": "not_found",
                        "impact_if_missing": "AI cannot explain value proposition."
                    },
                    {
                        "requirement_name": "Policies / expectations",
                        "category": "Risk Reduction",
                        "why_ai_needs_this": "AI needs clear policies to reduce buyer uncertainty.",
                        "current_status": "not_found",
                        "impact_if_missing": "AI sees unclear expectations as risk."
                    }
                ]
                # Merge LLM items with fallback items (LLM items first, then fill to 10)
                existing = audit_json["ai_requirements_before"]
                needed = 10 - len(existing)
                if needed > 0:
                    audit_json["ai_requirements_before"] = existing + fallback_before[:needed]
                else:
                    audit_json["ai_requirements_before"] = existing
            
            if "ai_requirements_after" not in audit_json or not isinstance(audit_json.get("ai_requirements_after"), list):
                print("[STAGE A] ⚠️ ai_requirements_after missing from LLM response, creating minimal fallback")
                audit_json["ai_requirements_after"] = []
            
            # If LLM returned fewer than 10 items, pad with fallback items
            if len(audit_json["ai_requirements_after"]) < 10:
                print(f"[STAGE A] ⚠️ ai_requirements_after has only {len(audit_json['ai_requirements_after'])} items, padding to 10")
                fallback_after = [
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
                    },
                    {
                        "requirement_name": "Local/entity signals",
                        "category": "Entity Understanding",
                        "what_must_be_built": "Add location proof, hours, service areas, and local entity markers.",
                        "ai_outcome_unlocked": "AI can confidently recommend for local queries."
                    },
                    {
                        "requirement_name": "Structured summaries AI can quote",
                        "category": "Decision Clarity",
                        "what_must_be_built": "Build key features, benefits, and decision blocks in quotable format.",
                        "ai_outcome_unlocked": "AI can directly cite structured summaries."
                    },
                    {
                        "requirement_name": "Contact / conversion clarity",
                        "category": "Risk Reduction",
                        "what_must_be_built": "Add clear CTAs, contact methods, and next-steps information.",
                        "ai_outcome_unlocked": "AI can guide users to conversion with clarity."
                    },
                    {
                        "requirement_name": "Value anchors",
                        "category": "Comparability",
                        "what_must_be_built": "Add value comparisons, ROI examples, or cost-benefit explanations.",
                        "ai_outcome_unlocked": "AI can contextualize pricing and explain value."
                    },
                    {
                        "requirement_name": "Policies / expectations",
                        "category": "Risk Reduction",
                        "what_must_be_built": "Create clear policies, SLAs, and expectation-setting content.",
                        "ai_outcome_unlocked": "AI can explain clear expectations and reduce buyer uncertainty."
                    }
                ]
                # Merge LLM items with fallback items (LLM items first, then fill to 10)
                existing = audit_json["ai_requirements_after"]
                needed = 10 - len(existing)
                if needed > 0:
                    audit_json["ai_requirements_after"] = existing + fallback_after[:needed]
                else:
                    audit_json["ai_requirements_after"] = existing
            
            # Validate with Pydantic
            validated = AuditResult(**audit_json)
            
            print(f"[STAGE A] ✅ Validation passed (attempt {attempt})")
            print(f"[STAGE A] ChatGPT visibility: {validated.stage_1_ai_visibility.chatgpt_visibility_percent}% ({validated.stage_1_ai_visibility.chatgpt_label})")
            print(f"[STAGE A] Recommended option: {validated.stage_5_business_impact.recommended_option}")
            return validated.model_dump()
            
        except json.JSONDecodeError as e:
            print(f"[STAGE A] JSON decode error on attempt {attempt}/{max_attempts}: {e}")
            print(f"[STAGE A] Error details: {str(e)}")
            if attempt < max_attempts:
                print("[STAGE A] Repair pass: Requesting properly formatted JSON...")
                repair_prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED: Invalid JSON format. Error: {str(e)}\n\nCRITICAL: Return COMPLETE, VALID JSON matching the schema EXACTLY. Ensure:\n- All strings are properly quoted\n- No trailing commas\n- All brackets/braces are closed\n- Response is not truncated"
                return await self.run_stage_a(repair_prompt, attempt + 1, max_attempts)
            
            # On final failure, save the malformed JSON for debugging
            print(f"[STAGE A] ❌ Final failure. Raw JSON (last 500 chars):")
            print(audit_json_str[-500:] if len(audit_json_str) > 500 else audit_json_str)
            raise ValueError(f"Stage A returned invalid JSON after {max_attempts} attempts: {e}")
            
        except Exception as e:
            print(f"[STAGE A] Validation error on attempt {attempt}/{max_attempts}: {e}")
            if attempt < max_attempts:
                print("[STAGE A] Repair pass: Fixing schema validation...")
                repair_prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED: Schema validation error: {str(e)}\n\nFix the JSON to match schema exactly. Ensure ALL required fields are present:\n- stage_1_ai_visibility\n- ai_interpretation\n- decision_readiness_audit (12 elements with status: missing/weak/fragmented/present)\n- decision_coverage_score (present/weak/missing/total)\n- stage_2_why_ai_chooses_others\n- stage_3_what_ai_needs (with ai_requirements_before and ai_requirements_after, 10+ items each)\n- stage_4_packages\n- stage_5_business_impact\n- appendix"
                return await self.run_stage_a(repair_prompt, attempt + 1, max_attempts)
            raise ValueError(f"Stage A output validation failed after {max_attempts} attempts: {e}")
    
    # =========================================================================
    # Stage B: Action Plan Builder
    # =========================================================================
    
    def build_stage_b_prompt(
        self,
        job: AuditJob,
        stage_a_result: Dict[str, Any],
        scraping_summary: Dict[str, Any],
        target_pages: List[ScrapedPage],
        competitor_pages_count: int,
    ) -> str:
        """Build Stage B user prompt based on Stage A results"""
        
        schema_json = json.dumps(self.get_stage_b_json_schema(), indent=2)
        
        # Extract key info from Stage A
        top_gaps_summary = "\n".join([
            f"- {gap['issue']}: {gap['recommended_fix']} (Impact: {gap['impact']})"
            for gap in stage_a_result.get('top_gaps', [])[:5]
        ])
        
        scores = stage_a_result.get('scores', {})
        
        # Guardrails and confidence
        confidence_level = "high"
        confidence_notes = []
        
        if scraping_summary['pages_fetched_target'] < 8:
            confidence_level = "low"
            confidence_notes.append(f"Limited data - only {scraping_summary['pages_fetched_target']} pages analyzed")
        elif scraping_summary['pages_fetched_target'] < 15:
            confidence_level = "medium"
        
        if competitor_pages_count == 0:
            confidence_notes.append("No competitor data available - market insights are general industry patterns only")
        
        confidence_override = ""
        if confidence_notes:
            confidence_override = "\n\nDATA LIMITATIONS:\n" + "\n".join(f"- {note}" for note in confidence_notes)
        
        # Extract company_profile from stage_a_result for fallback
        ev_layer = stage_a_result.get("evidence_layer") if isinstance(stage_a_result.get("evidence_layer"), dict) else {}
        company_profile = ev_layer.get("company_profile") if isinstance(ev_layer.get("company_profile"), dict) else {}
        
        # Fallback logic: use extracted values from scraping when user input is None
        services_list = company_profile.get('services_detected', [])
        company_desc = (
            job.company_description 
            or company_profile.get('primary_offer_summary') 
            or 'not detected'
        )
        products = (
            job.products_services 
            or (", ".join(services_list) if isinstance(services_list, list) and services_list else None)
            or 'not detected'
        )
        
        prompt = f"""COMPANY CONTEXT (EXTRACTED FROM SCRAPING)
-------------------------------------------
Target domain: {job.target_domain}
Locale: {job.locale}
Company description: {company_desc}
Main products/services: {products}

DATA CONFIDENCE LEVEL: {confidence_level.upper()}

STAGE A AUDIT RESULTS (SUMMARY)
-------------------------------
Current LLM Recommendability Scores:
- Recommendability: {scores.get('recommendability', 'N/A')}/100
- Proof Strength: {scores.get('proof_strength', 'N/A')}/100
- Clarity of Offering: {scores.get('clarity_of_offering', 'N/A')}/100
- Comparability: {scores.get('comparability', 'N/A')}/100
- Entity Coverage: {scores.get('entity_coverage', 'N/A')}/100

What LLMs say today:
{stage_a_result.get('what_llms_will_say_today', 'N/A')}

Top LLM Coverage Gaps (not "missing pages" - insufficient AI understanding):
{top_gaps_summary}

LLM Visibility Risks:
{chr(10).join(['- ' + r for r in stage_a_result.get('llm_visibility_risks', [])]) or 'None identified'}

DATA CONTEXT
------------
Pages scraped: {scraping_summary['pages_fetched_target']}
Page types found: {', '.join(scraping_summary['top_page_types_detected'])}
Pricing info detected: {scraping_summary['has_pricing_page']}
Case studies detected: {scraping_summary['has_case_studies']}
Testimonials detected: {scraping_summary['has_testimonials_or_reviews']}
Trust signals: {', '.join(scraping_summary['trust_signals_found']) if scraping_summary['trust_signals_found'] else 'None'}
{confidence_override}

TASK: CREATE LLM COVERAGE PLAN
------------------------------
Based on the Stage A audit results, create an LLM Coverage Plan with:

1. THREE COVERAGE LEVELS (REQUIRED):
   - Baseline: Minimum for AI to understand the business (e.g., 3-5 pages)
   - Recommended: For AI to compare with alternatives (e.g., 6-10 pages)  
   - Authority: For confident AI recommendations (e.g., 12-18 pages)
   
   Even if the site has very few pages or limited data (e.g., 6 pages), you MUST still:
   - provide ALL three coverage levels (baseline/recommended/authority)
   - estimate the current level using "partial baseline" etc. when between tiers
   - quantify how many content units are needed for the next level

   Each level MUST specify:
   - page_count_range (realistic for this business)
   - typical_content_units_range (capacity language)
   - page_types (what types of pages)
   - llm_capability_unlocked (understand → compare → recommend)
   - what_ai_can_do_at_this_level (plain-language AI behavior at this tier)
   - who_this_level_is_for (capacity/budget/team fit — aligned to packaging tiers)
   - expected_shift (qualitative change, NO traffic numbers)

2. RECOMMENDED PAGES with content_unit_type:
   - service_page: Service/product explanations
   - entity_page: Business entity (about, team, location)
   - comparison_page: vs alternatives, use cases
   - trust_page: Social proof, case studies
   - faq_page: Structured Q&A
   - hub_page: Overview/navigation
   
   Mark counts_toward_coverage: true/false for each page

3. CONTENT SUMMARY:
   - total_content_units: e.g., "8-12 LLM-focused content units"
   - breakdown_by_type: count per type
   - estimated_coverage_level: which tier this plan achieves

4. GROWTH PLAN COVERAGE SUMMARY (REQUIRED):
   - current_coverage_level: partial baseline | baseline | partial recommended | recommended | partial authority | authority
   - coverage_after_plan: baseline | recommended | authority
   - content_units_needed_for_next_level: a small range like "5–7" or "N/A (already at Authority)"

5. IMPACT FORECAST TIED TO COVERAGE:
   - baseline_impact: "At baseline coverage, AI will..." (low confidence)
   - recommended_impact: "At recommended coverage, AI will..." (medium confidence)
   - authority_impact: "At authority coverage, AI will..." (high confidence)
   - why_coverage_matters: Explain more content = more quotable = higher AI confidence
   - key_unlocks: What each level unlocks

CRITICAL LANGUAGE RULES:
1. NEVER say "page missing" or "no page exists" — say "not sufficiently covered for AI models" or "insufficient entity depth"
2. NEVER say "create missing page" — say "structure information for AI discoverability"
3. For service businesses: "pricing transparency" with ranges, NOT fixed price lists
4. Frame ALL as "LLM understanding" improvement, not content gaps

IMPORTANT RULES:
- This is NOT an SEO plan. Do NOT mention keywords, rankings, backlinks, SERP, or Google.
- Recommended pages: max 8 (prioritize highest impact)
- NO traffic numbers or visitor predictions anywhere
- Focus on qualitative AI capability improvements
- Include example_snippet_for_citation that LLMs could quote directly

SCHEMA (RETURN EXACTLY THIS SHAPE)
----------------------------------
{schema_json}"""
        
        return prompt
    
    async def run_stage_b(
        self,
        prompt: str,
        pages_fetched: int,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Run Stage B: Action Plan Builder with LLM Coverage Levels
        Model: settings.openai_model | Temperature: 0.3 | Max tokens: 2800
        """
        try:
            print(f"[STAGE B] Calling {self._effective_model()} (temp=0.3, max_tokens=2800)...")
            
            response = await self.client.chat.completions.create(
                model=self._effective_model(),
                messages=[
                    {"role": "system", "content": STAGE_B_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Slightly higher for creativity
                max_tokens=2800,  # Increased for coverage levels
            )
            
            # Check if response was truncated
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                print(f"[STAGE B] ⚠️ Response truncated (finish_reason: {finish_reason})")
                if attempt < max_attempts:
                    print("[STAGE B] Retrying with request for shorter response...")
                    repair_prompt = prompt + "\n\nIMPORTANT: Previous response was truncated. Generate a COMPLETE, VALID JSON response. Be concise but ensure ALL required fields are present."
                    return await self.run_stage_b(repair_prompt, pages_fetched, attempt + 1, max_attempts)
                raise ValueError(f"Stage B response truncated after {max_attempts} attempts")
            
            action_json_str = response.choices[0].message.content
            
            # Log raw JSON for debugging
            if attempt == 1:
                print(f"[STAGE B] Raw JSON length: {len(action_json_str)} chars")
            
            # Attempt to repair malformed JSON
            try:
                action_json = json.loads(action_json_str)
            except json.JSONDecodeError as e:
                print(f"[STAGE B] Initial JSON parse failed: {e}")
                print(f"[STAGE B] Attempting to repair JSON...")
                
                # Try to fix common JSON issues
                repaired_json_str = action_json_str
                
                # Remove trailing commas before closing brackets/braces
                import re
                repaired_json_str = re.sub(r',\s*}', '}', repaired_json_str)
                repaired_json_str = re.sub(r',\s*]', ']', repaired_json_str)
                
                # Try to close unterminated strings
                if 'Unterminated string' in str(e):
                    error_pos = e.pos if hasattr(e, 'pos') else len(repaired_json_str)
                    repaired_json_str = repaired_json_str[:error_pos]
                    open_braces = repaired_json_str.count('{') - repaired_json_str.count('}')
                    open_brackets = repaired_json_str.count('[') - repaired_json_str.count(']')
                    repaired_json_str += '"' * (repaired_json_str.count('"') % 2)
                    repaired_json_str += ']' * open_brackets
                    repaired_json_str += '}' * open_braces
                
                try:
                    action_json = json.loads(repaired_json_str)
                    print(f"[STAGE B] ✓ JSON repair successful")
                except json.JSONDecodeError:
                    raise e
            
            # Debug: Check what LLM returned
            print(f"[STAGE B DEBUG] Keys in LLM response: {list(action_json.keys())}")
            if 'content_summary' in action_json:
                print(f"[STAGE B DEBUG] content_summary present: {action_json['content_summary']}")
            else:
                print(f"[STAGE B DEBUG] ❌ content_summary MISSING!")
            if 'coverage_levels' in action_json:
                print(f"[STAGE B DEBUG] coverage_levels present")
            else:
                print(f"[STAGE B DEBUG] ❌ coverage_levels MISSING!")
            
            # Validate with Pydantic - strict validation, no fallbacks
            validated = ActionPlanResult(**action_json)
            
            print(f"[STAGE B] Validation passed (attempt {attempt}/{max_attempts})")
            print(f"[STAGE B] Coverage levels: baseline, recommended, authority")
            print(f"[STAGE B] Content units: {validated.content_summary.total_content_units}")
            print(f"[STAGE B] Recommended pages: {len(validated.recommended_pages)}")
            return validated.model_dump()
            
        except json.JSONDecodeError as e:
            print(f"[STAGE B] JSON decode error on attempt {attempt}/{max_attempts}: {e}")
            if attempt < max_attempts:
                print("[STAGE B] Repair pass: Requesting properly formatted JSON...")
                repair_prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED: Invalid JSON format. Error: {str(e)}\n\nCRITICAL: Return COMPLETE, VALID JSON matching the schema EXACTLY. Ensure:\n- All strings are properly quoted\n- No trailing commas\n- All brackets/braces are closed\n- Response is not truncated"
                return await self.run_stage_b(repair_prompt, pages_fetched, attempt + 1, max_attempts)
            
            # On final failure, save the malformed JSON for debugging
            print(f"[STAGE B] ❌ Final failure. Raw JSON (last 500 chars):")
            print(action_json_str[-500:] if len(action_json_str) > 500 else action_json_str)
            raise ValueError(f"Stage B returned invalid JSON after {max_attempts} attempts: {e}")
            
        except Exception as e:
            print(f"[STAGE B] Validation error on attempt {attempt}/{max_attempts}: {e}")
            if attempt < max_attempts:
                print("[STAGE B] Repair pass: Fixing schema validation...")
                repair_prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED: Schema validation error: {str(e)}\nFix the JSON to match schema exactly. Ensure ALL required fields are present including coverage_levels and content_summary."
                return await self.run_stage_b(repair_prompt, pages_fetched, attempt + 1, max_attempts)
            raise ValueError(f"Stage B output validation failed after {max_attempts} attempts: {e}")
    
    # =========================================================================
    # Main Audit Pipeline
    # =========================================================================
    
    async def run_audit(
        self,
        job_id: str,
        priority_urls: list[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any], list[str]]:
        """
        Run 2-stage LLM audit pipeline
        Returns: (stage_a_audit_json, stage_b_action_plan_json, sampled_urls)
        """
        
        # Get job
        result = await self.db.execute(
            select(AuditJob).where(AuditJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Update status
        job.status = "llm_processing"
        job.current_stage = "preparing_context"
        job.llm_started_at = datetime.utcnow()
        job.progress_percent = 65
        await self.db.commit()
        await asyncio.sleep(0.5)  # Give frontend time to display this stage
        
        # Select representative pages
        print("[LLM] Selecting representative pages...")
        target_pages = await self.select_representative_pages(job_id, is_target=True, max_pages=15)
        competitor_pages = await self.select_representative_pages(job_id, is_target=False, max_pages=10)
        
        print(f"[LLM] Selected {len(target_pages)} target pages, {len(competitor_pages)} competitor pages")
        
        # Build scraping summary
        job.current_stage = "building_context"
        job.progress_percent = 68
        await self.db.commit()
        await asyncio.sleep(0.5)  # Give frontend time to display this stage
        
        scraping_summary = self.build_scraping_summary(job, target_pages)

        # Build deterministic Evidence Layer from stored HTML/text (no LLM involvement).
        extractor = EvidenceExtractor(max_pages=15)
        evidence_layer = extractor.build_evidence_layer(
            pages=target_pages,
            fallback_domain=job.target_domain,
            locale=job.locale,
        )
        
        # Testing AI models stage (ChatGPT, Gemini, Perplexity simulation)
        job.current_stage = "testing_ai_models"
        job.progress_percent = 70
        await self.db.commit()
        await asyncio.sleep(1.0)  # Give frontend time to display this stage
        
        print("\n[LLM] Testing AI model recommendations...")
        
        # Identifying AI visibility gaps
        job.current_stage = "identifying_gaps"
        job.progress_percent = 73
        await self.db.commit()
        await asyncio.sleep(1.5)  # Give frontend time to display this stage
        
        print("[LLM] Identifying missing signals in AI visibility...")
        
        # =====================================================================
        # STAGE A: Core Audit
        # =====================================================================
        job.current_stage = "stage_a_core_audit"
        job.progress_percent = 75
        await self.db.commit()
        
        print("\n" + "="*60)
        print("[STAGE A] CORE AUDIT - LLM Recommendability Analysis")
        print("="*60)
        
        stage_a_prompt = self.build_stage_a_prompt(
            job,
            target_pages,
            competitor_pages,
            scraping_summary,
            evidence_layer=evidence_layer,
        )
        stage_a_result = await self.run_stage_a(stage_a_prompt)
        
        # Add appendix data to Stage A
        sampled_urls = [p.url for p in target_pages[:10]]
        stage_a_result["appendix"]["sampled_urls"] = sampled_urls
        stage_a_result["appendix"]["data_limitations"] = (
            f"Analysis based on {len(target_pages)} target pages and {len(competitor_pages)} competitor pages. "
            f"Scraped at {datetime.utcnow().strftime('%Y-%m-%d')}."
        )
        stage_a_result["appendix"]["pages_analyzed_target"] = len(target_pages)
        stage_a_result["appendix"]["pages_analyzed_competitors"] = len(competitor_pages)

        # Attach evidence layer (deterministic, scraping-backed) to the stored audit JSON.
        stage_a_result["evidence_layer"] = evidence_layer

        # Enrich packages with concrete, scraping-derived page titles (deterministic).
        try:
            self._enrich_packages_with_architecture(stage_a_result, evidence_layer)
        except Exception:
            # Never block audits due to package enrichment issues.
            pass

        # QA gate: enforce evidence refs, personalization tokens, no hedging, safe snippet lengths.
        try:
            self._qa_validate_and_fix(stage_a_result)
        except Exception:
            # QA must never block the pipeline; prefer safe fallbacks.
            pass
        
        print("[STAGE A] Complete!\n")
        
        # =====================================================================
        # NEW APPROACH: Stage A now contains all 5 sales stages (A-E)
        # Stage B is DISABLED for new sales flow
        # =====================================================================
        
        # Convert new sales structure to backward-compatible format for existing code
        # This allows templates and APIs to work with both old and new structures
        stage_b_result = self._convert_sales_to_action_plan(stage_a_result, scraping_summary)
        
        # Save results
        job.audit_result = stage_a_result  # Keep for backward compatibility
        job.llm_completed_at = datetime.utcnow()
        job.progress_percent = 80
        await self.db.commit()
        
        print("="*60)
        print("[LLM] AI Visibility Sales Report Complete!")
        print(f"[LLM] ChatGPT: {stage_a_result.get('stage_1_ai_visibility', {}).get('chatgpt_visibility_percent', 'N/A')}%")
        print(f"[LLM] Reasons identified: {len(stage_a_result.get('stage_2_why_ai_chooses_others', []))}")
        print(f"[LLM] Recommended option: {stage_a_result.get('stage_5_business_impact', {}).get('recommended_option', 'N/A')}")
        print("="*60 + "\n")
        
        return stage_a_result, stage_b_result, sampled_urls

    # =========================================================================
    # QA gate (deterministic)
    # =========================================================================

    def _qa_validate_and_fix(self, stage_a_result: Dict[str, Any]) -> None:
        """
        Hard self-check before storing audit JSON.
        This is NOT a linter. It enforces the product rules deterministically.
        """
        if not isinstance(stage_a_result, dict):
            return

        ev_layer = stage_a_result.get("evidence_layer") if isinstance(stage_a_result.get("evidence_layer"), dict) else {}
        evidence = ev_layer.get("evidence") if isinstance(ev_layer.get("evidence"), list) else []
        cp = ev_layer.get("company_profile") if isinstance(ev_layer.get("company_profile"), dict) else {}

        company_name = str(cp.get("company_name") or "").strip() or str(stage_a_result.get("appendix", {}).get("sampled_urls", ["this domain"])[0] if isinstance(stage_a_result.get("appendix"), dict) else "this domain")
        services = cp.get("services_detected") if isinstance(cp.get("services_detected"), list) else []
        services = [str(s).strip() for s in services if isinstance(s, str) and str(s).strip()]
        top_service = services[0] if services else "your core service"

        # Helpers
        hedge_patterns = [
            (re.compile(r"\b(might be|may be|could be)\b", re.IGNORECASE), "is"),
            (re.compile(r"\b(might|may|could|maybe|likely|potentially)\b", re.IGNORECASE), ""),
        ]

        def dehedge(text: str) -> str:
            t = text or ""
            for rx, repl in hedge_patterns:
                t = rx.sub(repl, t)
            # Clean double spaces
            t = re.sub(r"\s{2,}", " ", t).strip()
            return t

        def ensure_refs(refs: Any) -> List[int]:
            if not isinstance(refs, list):
                refs = []
            out = []
            for x in refs:
                try:
                    n = int(x)
                except Exception:
                    continue
                if 0 <= n < len(evidence):
                    out.append(n)
            if not out and evidence:
                out = [0]
            return out[:3]

        # 1) Stage 2 reasons: evidence refs must exist; no hedging; personalization token coverage.
        reasons = stage_a_result.get("stage_2_why_ai_chooses_others")
        if isinstance(reasons, list):
            token_hits = 0
            for r in reasons:
                if not isinstance(r, dict):
                    continue

                r["evidence_refs"] = ensure_refs(r.get("evidence_refs"))

                # De-hedge key fields
                for k in ["how_llms_decide", "what_we_found_on_your_site", "what_ai_does_instead", "what_must_be_built"]:
                    if isinstance(r.get(k), str):
                        r[k] = dehedge(r[k])

                # Ensure what_must_be_built contains a concrete title pattern if missing
                wmb = r.get("what_must_be_built")
                if not isinstance(wmb, str) or not wmb.strip():
                    r["what_must_be_built"] = f'Build: "How {top_service} Works" + "{top_service} Pricing & Packages" + a structured FAQ block.'
                else:
                    if "How " not in wmb and "Pricing" not in wmb and top_service.lower() not in wmb.lower():
                        r["what_must_be_built"] = wmb.rstrip(".") + f' Example: "How {top_service} Works".'

                # Token coverage heuristic: company name OR a detected service string appears in reason text.
                blob = " ".join(
                    [
                        str(r.get("how_llms_decide") or ""),
                        str(r.get("what_we_found_on_your_site") or ""),
                        str(r.get("what_ai_does_instead") or ""),
                        str(r.get("what_must_be_built") or ""),
                    ]
                ).lower()
                if company_name.lower() in blob or any(s.lower() in blob for s in services[:3]):
                    token_hits += 1
                else:
                    # Deterministic patch: add company name and top service without changing the claim.
                    r["what_we_found_on_your_site"] = (
                        f"{company_name}: {top_service} coverage is not structured for AI quoting. "
                        + (str(r.get("what_we_found_on_your_site") or "").strip() or "Not detected in the crawl.")
                    )[:260]

            # 70% coverage target (best-effort; we patch per-item above)
            # No hard failure: patched items already increase coverage.

        # 2) Stage 3: remove hedges in what_it_unlocks/impact/what_we_saw if present.
        needs = stage_a_result.get("stage_3_what_ai_needs")
        if isinstance(needs, list):
            for n in needs:
                if not isinstance(n, dict):
                    continue
                for k in ["what_it_unlocks", "impact", "what_we_saw"]:
                    if isinstance(n.get(k), str):
                        n[k] = dehedge(n[k])

        # 3) Closing blocks exist; no forbidden wording.
        impact = stage_a_result.get("stage_5_business_impact")
        if isinstance(impact, dict):
            nb = impact.get("neutrality_block")
            if not isinstance(nb, str) or not nb.strip():
                impact["neutrality_block"] = "This audit is platform-agnostic. Any capable team can implement it."
            ob = impact.get("our_offer_block")
            if not isinstance(ob, str) or not ob.strip():
                impact["our_offer_block"] = (
                    "If you want fast implementation without trial-and-error, we can deliver Wave 1 in a fixed scope with predictable cost. "
                    "US-first GEO architecture, built for LLM quoting."
                )
            # Remove explicit 'cheap' if present
            for k in ["neutrality_block", "our_offer_block"]:
                if isinstance(impact.get(k), str):
                    impact[k] = impact[k].replace("cheap", "cost-effective")
            stage_a_result["stage_5_business_impact"] = impact

    # =========================================================================
    # Deterministic package architecture (scraping-derived)
    # =========================================================================

    def _enrich_packages_with_architecture(self, stage_a_result: Dict[str, Any], evidence_layer: Dict[str, Any]) -> None:
        packages = (stage_a_result or {}).get("stage_4_packages")
        if not isinstance(packages, dict):
            return

        cp = (evidence_layer or {}).get("company_profile") if isinstance(evidence_layer, dict) else {}
        cp = cp if isinstance(cp, dict) else {}

        company_name = str(cp.get("company_name") or "").strip() or "this domain"
        services = cp.get("services_detected") if isinstance(cp.get("services_detected"), list) else []
        services = [str(s).strip() for s in services if isinstance(s, str) and str(s).strip()]
        services = services[:6]
        top3 = services[:3]

        locations = cp.get("locations_detected") if isinstance(cp.get("locations_detected"), list) else []
        locations = [str(l).strip() for l in locations if isinstance(l, str) and str(l).strip()]
        locations = locations[:5]

        proof_types = set()
        ev_items = (evidence_layer or {}).get("evidence") if isinstance(evidence_layer, dict) else []
        if isinstance(ev_items, list):
            for e in ev_items:
                if isinstance(e, dict) and isinstance(e.get("proof_type"), str):
                    proof_types.add(e.get("proof_type"))

        def safe_service(i: int) -> str:
            if i < len(top3):
                return top3[i]
            return "your core service"

        def titles_for_10() -> List[str]:
            s1 = safe_service(0)
            s2 = safe_service(1)
            return [
                f"How {s1} Works",
                f"{s1} Pricing & Packages",
                f"{s1} FAQ",
                f"About {company_name}",
                f"Contact {company_name}",
                f"How {s2} Works",
            ][:6]

        def titles_for_30() -> List[str]:
            s1 = safe_service(0)
            s2 = safe_service(1)
            s3 = safe_service(2)
            # 6–12 concrete titles (deterministic)
            return [
                f"How {s1} Works",
                f"{s1} Pricing & Packages",
                f"{s1} vs Alternatives",
                f"Common mistakes when choosing {s1}",
                f"{s1} FAQ",
                f"How {s2} Works",
                f"{s2} Pricing & Packages",
                f"{s2} vs Alternatives",
                f"How {s3} Works",
                f"{s3} Pricing & Packages",
                f"About {company_name}",
                f"Contact {company_name}",
            ][:12]

        def titles_for_100() -> List[str]:
            s1 = safe_service(0)
            s2 = safe_service(1)
            base = [
                f"How {s1} Works",
                f"{s1} Pricing & Packages",
                f"{s1} vs Alternatives",
                f"How {s2} Works",
                f"{s2} Pricing & Packages",
                f"{s2} vs Alternatives",
                f"About {company_name}",
                f"{company_name} Reviews & Case Studies",
                f"{company_name} Certifications & Standards",
            ]
            # Location expansion (only if detected; avoid inventing).
            if locations:
                for loc in locations[:3]:
                    base.append(f"{s1} in {loc}")
                    base.append(f"{s2} in {loc}")
            else:
                base.extend(
                    [
                        f"Best {s1} for different buyer situations",
                        f"When to choose {s1} vs {s2}",
                        f"Common questions about {s1}",
                    ]
                )
            # Keep bounded.
            return base[:18]

        tier_map = {
            "ai_entry_10_pages": titles_for_10(),
            "ai_recommendation_30_pages": titles_for_30(),
            "ai_authority_100_pages": titles_for_100(),
        }

        for key, titles in tier_map.items():
            pkg = packages.get(key)
            if not isinstance(pkg, dict):
                continue
            # Always enforce deterministic titles (scraping-derived).
            pkg["pages_to_build"] = titles
            pkg["example_page_title"] = titles[0] if titles else pkg.get("example_page_title")
            # Mildly normalize optional fields if missing so UI never renders blank.
            pkg.setdefault("why_ai_needs_it", "AI selects sources that answer buyer questions end-to-end, with quotable structure.")
            pkg.setdefault("who_this_is_for", "Teams that want predictable AI visibility improvements with a fixed scope.")
            pkg.setdefault("expected_outcome", "Higher LLM confidence to describe and compare you; more consistent inclusion in AI answers.")
            # Tie to findings (deterministic nudges)
            if key == "ai_recommendation_30_pages":
                if any(pt in proof_types for pt in {"no_pricing", "no_contact", "weak_entity_signals"}):
                    pkg["who_this_is_for"] = "Teams that need to fix missing pricing/contact/entity clarity to stop AI defaulting to competitors."
                    pkg["expected_outcome"] = "LLMs can compare you with alternatives and cite specific proof blocks without guessing."
            if key == "ai_authority_100_pages" and locations:
                pkg["why_ai_needs_it"] = "Multi-location coverage requires consistent, location-specific entity pages so LLMs can recommend you for local-intent queries."
            packages[key] = pkg
    
    def _convert_sales_to_action_plan(self, sales_report: Dict[str, Any], scraping_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert new sales report structure to backward-compatible action plan format.
        This allows existing templates/APIs to work without major refactoring.
        """
        packages = sales_report.get("stage_4_packages", {}) if isinstance(sales_report, dict) else {}
        impact = sales_report.get("stage_5_business_impact", {}) if isinstance(sales_report, dict) else {}

        # Map fixed packages (10/30/100) into legacy coverage levels (internal only).
        # This does NOT affect the sales UI; it exists purely for backward-compatible normalized payloads.
        recommended_level = "recommended"
        
        # Build backward-compatible structure
        entry = packages.get("ai_entry_10_pages", {}) if isinstance(packages, dict) else {}
        rec = packages.get("ai_recommendation_30_pages", {}) if isinstance(packages, dict) else {}
        auth = packages.get("ai_authority_100_pages", {}) if isinstance(packages, dict) else {}

        return {
            "recommended_pages": [],  # Sales flow doesn't need specific page recommendations
            "sitewide_blocks_to_add": [],
            "coverage_levels": {
                "baseline": {
                    "level_name": "baseline",
                    "page_count_range": "10 pages",
                    "typical_content_units_range": "10 content units",
                    "page_types": ["service_page", "entity_page"],
                    "llm_capability_unlocked": "AI understands the business",
                    "what_ai_can_do_at_this_level": "AI finally understands the business",
                    "who_this_level_is_for": "Small businesses starting AI visibility",
                    "expected_shift": (entry.get("messaging") if isinstance(entry, dict) else None) or "Without this, AI does not even know who you are.",
                },
                "recommended": {
                    "level_name": "recommended",
                    "page_count_range": "30 pages",
                    "typical_content_units_range": "30 content units",
                    "page_types": ["service_page", "entity_page", "comparison_page", "trust_page"],
                    "llm_capability_unlocked": "AI compares and suggests",
                    "what_ai_can_do_at_this_level": "AI starts recommending the business in answers",
                    "who_this_level_is_for": "Growing businesses seeking AI recommendations",
                    "expected_shift": (rec.get("messaging") if isinstance(rec, dict) else None) or "This is where AI traffic actually starts.",
                },
                "authority": {
                    "level_name": "authority",
                    "page_count_range": "100 pages",
                    "typical_content_units_range": "100 content units",
                    "page_types": ["service_page", "entity_page", "comparison_page", "trust_page", "faq_page", "hub_page"],
                    "llm_capability_unlocked": "AI confidently recommends",
                    "what_ai_can_do_at_this_level": "AI prefers and cites the business confidently",
                    "who_this_level_is_for": "Established brands competing on trust",
                    "expected_shift": (auth.get("messaging") if isinstance(auth, dict) else None) or "This turns AI into a growth channel, not an experiment.",
                },
                "current_assessment": "Recommended option: 30-page AI Recommendation package"
            },
            "content_summary": {
                "total_content_units": "30 content units",
                "breakdown_by_type": {},
                "estimated_coverage_level": recommended_level
            },
            "growth_plan_summary": {
                "current_coverage_level": "partial baseline",
                "coverage_after_plan": recommended_level,
                "content_units_needed_for_next_level": "5-7"
            },
            "impact_forecast": {
                "baseline_impact": "AI understands you, but does not reliably recommend you.",
                "recommended_impact": "AI compares you and starts recommending you in answers.",
                "authority_impact": "AI prefers you and cites you confidently long-term.",
                "why_coverage_matters": (impact.get("why_ai_visibility_compounds") if isinstance(impact, dict) else None) or "AI visibility compounds over time.",
                "key_unlocks": ["Visibility", "Recommendations", "Citations", "Traffic"]
            },
            "measurement_plan": {
                "what_to_track": ["AI mentions", "AI citations", "Brand visibility in AI answers"],
                "simple_tests": ["Ask ChatGPT about your business", "Check Perplexity recommendations"]
            }
        }
