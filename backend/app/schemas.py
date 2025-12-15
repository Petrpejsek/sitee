"""Pydantic schemas for API"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


# Request schemas
class AuditCreateRequest(BaseModel):
    """Request to create a new audit - ONLY domain required, everything else extracted from scraping"""
    target_domain: str = Field(..., description="Main domain to audit (without https://)")


# Response schemas
class AuditJobResponse(BaseModel):
    """Audit job response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Input
    target_domain: str
    competitor_domains: List[str]
    locale: str
    company_description: Optional[str]
    products_services: Optional[str]
    
    # Status
    status: str
    current_stage: Optional[str]
    progress_percent: int
    error_message: Optional[str]
    
    # Outputs
    audit_result: Optional[Dict[str, Any]]
    report_pdf_path: Optional[str]
    report_html_path: Optional[str]
    
    # Metadata
    total_pages_scraped: int
    scraping_completed_at: Optional[datetime]
    llm_completed_at: Optional[datetime]
    report_generated_at: Optional[datetime]
    
    # Debug info (for failed jobs)
    scrape_debug: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class AuditCreateResponse(BaseModel):
    """Response after creating audit"""
    id: UUID
    status: str
    message: str


# =============================================================================
# AI VISIBILITY SALES REPORT SCHEMA (STAGES 1–5)
# =============================================================================

class Stage1AIVisibility(BaseModel):
    """STAGE 1 — AI VISIBILITY (DRAMA)"""
    chatgpt_visibility_percent: int = Field(..., ge=0, le=100, description="ChatGPT visibility 0–100")
    chatgpt_label: Literal["Poor", "Limited", "Strong"] = Field(..., description="Visibility label")
    gemini_visibility_percent: int = Field(..., ge=0, le=100, description="Gemini visibility 0–100")
    gemini_label: Literal["Poor", "Limited", "Strong"] = Field(..., description="Visibility label")
    perplexity_visibility_percent: int = Field(..., ge=0, le=100, description="Perplexity visibility 0–100")
    perplexity_label: Literal["Poor", "Limited", "Strong"] = Field(..., description="Visibility label")
    hard_sentence: str = Field(..., description="ONE hard sentence: competitors get recommended instead")


class MissingElement(BaseModel):
    """Missing understanding element that prevents AI recommendations"""
    key: str = Field(..., description="Element key (e.g., service_differentiation, pricing_structure)")
    label: str = Field(..., description="Human-readable label (e.g., 'No clear service differentiation')")
    impact: str = Field(..., description="Impact on AI recommendations (1 sentence)")
    severity: Literal["critical", "supporting"] = Field(..., description="Problem severity")


class AIInterpretation(BaseModel):
    """
    SECTION 02 — AI INTERPRETATION
    What AI currently understands vs. what is missing
    """
    summary: str = Field(..., description="3-4 sentence summary of what AI understands from analyzed content (no superlatives, no marketing)")
    confidence: Literal["shallow", "partial", "strong"] = Field(..., description="AI understanding confidence level")
    based_on_pages: int = Field(..., ge=0, description="Number of pages this interpretation is based on")
    detected_signals: List[str] = Field(default_factory=list, max_length=8, description="Weak/generic signals AI currently recognizes")
    missing_elements: List[MissingElement] = Field(..., min_length=4, max_length=6, description="What AI cannot understand (4-6 elements)")


class DecisionReadinessItem(BaseModel):
    """
    SECTION 03A — DECISION READINESS AUDIT ELEMENT
    Each element represents a specific decision-level component AI systems need
    """
    element_name: str = Field(..., description="Name of decision element (e.g., 'Structured Service Pages', 'Pricing & Value Tables')")
    status: Literal["present", "weak", "missing"] = Field(..., description="Element status based on scraping")
    what_ai_requires: str = Field(..., description="ONE sentence: what AI systems expect for this element (specific, not generic)")
    what_we_found: str = Field(..., description="ONE sentence: what was found on the website (evidence-backed, no fabrication)")
    impact_on_recommendation: str = Field(..., description="ONE sentence: how this affects AI's ability to recommend (causal, not emotional)")
    evidence_refs: List[int] = Field(default_factory=list, description="Indexes into evidence_layer.evidence[]")


class Stage2Reason(BaseModel):
    """STAGE 2 — WHY AI CHOOSES OTHERS (CAUSE) - LEGACY, kept for backward compatibility"""
    # New audit-voice structure (required going forward)
    how_llms_decide: str = Field(..., description="One-sentence general fact about how LLMs decide")
    what_we_found_on_your_site: str = Field(..., description="One sentence grounded in evidence (no invented facts)")
    what_ai_does_instead: str = Field(..., description="What AI does instead because of it (consequence)")
    what_must_be_built: str = Field(..., description="One concrete build requirement")
    evidence_refs: List[int] = Field(default_factory=list, description="Indexes into evidence_layer.evidence[]")

    # Backward-compat (legacy template/UI fields)
    what_is_missing: Optional[str] = Field(default=None, description="Legacy: what is missing (kept for backward compatibility)")
    what_we_saw: Optional[str] = Field(default=None, description="Legacy: one concrete crawl observation (kept for backward compatibility)")


class Stage3Need(BaseModel):
    """STAGE 3 — WHAT AI NEEDS (SOLUTION) - LEGACY, kept for backward compatibility"""
    content_type: str = Field(..., description="Type of pages/content AI needs")
    what_it_unlocks: str = Field(..., description="What it unlocks for AI")
    status: Literal["not_found", "weak", "present"] = Field(..., description="Crawl-backed status")
    what_we_saw: str = Field(..., description="One concrete crawl observation (no URLs, no HTML)")
    impact: str = Field(..., description="Consequence in business language (why this matters)")
    evidence_refs: List[int] = Field(default_factory=list, description="Optional indexes into evidence_layer.evidence[]")


class AIRequirementBefore(BaseModel):
    """
    SECTION 04A — AI REQUIREMENTS (BEFORE STATE)
    What is currently missing/weak that prevents AI recommendations
    """
    requirement_name: str = Field(..., description="Specific AI requirement (e.g., 'Explicit service definitions', 'Pricing transparency')")
    category: Literal["Decision Clarity", "Comparability", "Trust & Authority", "Entity Understanding", "Risk Reduction"] = Field(
        ..., description="AI decision-layer category"
    )
    why_ai_needs_this: str = Field(..., description="Why AI systems need this (1 sentence)")
    current_status: Literal["not_found", "weak", "missing"] = Field(..., description="Current status based on scraping (not_found/missing = same meaning)")
    impact_if_missing: str = Field(..., description="Impact if this remains missing (1 sentence)")


class AIRequirementAfter(BaseModel):
    """
    SECTION 04B — AI REQUIREMENTS (AFTER STATE)
    What must be built to unlock AI recommendations
    """
    requirement_name: str = Field(..., description="Specific AI requirement (e.g., 'Explicit service definitions', 'Pricing transparency')")
    category: Literal["Decision Clarity", "Comparability", "Trust & Authority", "Entity Understanding", "Risk Reduction"] = Field(
        ..., description="AI decision-layer category"
    )
    what_must_be_built: str = Field(..., description="Concrete build instruction (1 sentence)")
    ai_outcome_unlocked: str = Field(..., description="What AI capability this unlocks (1 sentence)")


class PagePackage(BaseModel):
    """Fixed page package (do not rename / do not change page counts)."""
    package_name: str = Field(..., description="Package name")
    pages: int = Field(..., description="Fixed page count: 10 / 30 / 100")
    purpose: str = Field(..., description="Purpose of the package")
    messaging: str = Field(..., description="Sales messaging line")
    what_ai_can_do: List[str] = Field(..., max_length=4, description="What AI can do at this package")
    ties_to_findings: str = Field(..., description="How this package addresses crawl findings (no URLs, no HTML)")

    # Evidence-first architecture extensions (non-breaking additions)
    why_ai_needs_it: Optional[str] = Field(default=None, description="1–2 sentences: why AI needs this tier")
    who_this_is_for: Optional[str] = Field(default=None, description="Who this tier is for")
    expected_outcome: Optional[str] = Field(default=None, description="Expected qualitative outcome (no promises)")
    pages_to_build: List[str] = Field(default_factory=list, description="Concrete page titles derived from services_detected")
    example_page_title: Optional[str] = Field(default=None, description="One example page title")


class Stage4Packages(BaseModel):
    """STAGE 4 — WHAT WE WILL BUILD (PACKAGES)"""
    ai_entry_10_pages: PagePackage
    ai_recommendation_30_pages: PagePackage
    ai_authority_100_pages: PagePackage


class Stage5BusinessImpact(BaseModel):
    """STAGE 5 — BUSINESS IMPACT (URGENCY)"""
    what_staying_invisible_costs: str = Field(..., description="What staying invisible costs")
    why_ai_visibility_compounds: str = Field(..., description="Why AI visibility compounds")
    why_waiting_makes_this_worse: str = Field(..., description="Why waiting makes this worse")
    competitor_preference_proof: str = Field(..., description="One proof sentence grounded in competitor crawl (or explicitly say competitor crawl unavailable)")
    recommended_option: str = Field(..., description="Must be: '30-page AI Recommendation package'")
    closing_line: str = Field(..., description="Must end with the required recommendation sentence")

    # Closing blocks (audit-neutrality + optional implementation offer)
    neutrality_block: Optional[str] = Field(default=None, description="Platform-agnostic neutrality statement")
    our_offer_block: Optional[str] = Field(default=None, description="Offer statement: fixed-scope, cost-effective, Wave 1 timing")


# =============================================================================
# Evidence Layer (deterministic, scraping-backed)
# =============================================================================

class EvidenceItem(BaseModel):
    claim: str = Field(..., description="What we claim")
    proof_type: str = Field(..., description="missing_page | fragmented_content | language_mismatch | no_pricing | no_contact | no_comparison | weak_entity_signals | ...")
    source_urls: List[str] = Field(default_factory=list, description="1–3 concrete URLs")
    snippets: List[str] = Field(default_factory=list, description="Short text excerpts/headings (bounded)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0–1 confidence based on detection strength")


class CompanyProfile(BaseModel):
    company_name: str = Field(..., description="From web; fallback: domain / 'this domain'")
    primary_offer_summary: str = Field(..., description="1–2 sentences extracted from homepage/services (or 'not detected')")
    services_detected: List[str] = Field(default_factory=list, description="Service/product names detected from headings")
    locations_detected: List[str] = Field(default_factory=list, description="Locations detected (if any)")
    primary_language_detected: str = Field(..., description="Detected primary language (or 'not detected')")
    top_pages: List[str] = Field(default_factory=list, description="Most important URLs by internal linking/nav")


class EvidencePage(BaseModel):
    url: str
    title: str = ""
    meta_description: str = ""
    text_excerpt: str = ""
    language: str = "not detected"
    h1: str = "not detected"
    headings: List[str] = Field(default_factory=list)
    cta_detected: List[str] = Field(default_factory=list)
    structured_data_types: List[str] = Field(default_factory=list)
    internal_links_top: List[str] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)


class EvidenceLayer(BaseModel):
    company_profile: CompanyProfile
    pages: List[EvidencePage] = Field(default_factory=list, description="Evidence page blocks (bounded)")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Universal evidence items used for citations")


class Appendix(BaseModel):
    """Appendix data"""
    sampled_urls: List[str]
    data_limitations: str
    pages_analyzed_target: int = Field(..., ge=0, description="How many target pages were analyzed")
    pages_analyzed_competitors: int = Field(..., ge=0, description="How many competitor pages were analyzed")


class DecisionCoverageScore(BaseModel):
    """
    SECTION 03 — DECISION COVERAGE SCORE
    Summary of how many decision elements are present vs missing
    """
    present: int = Field(..., ge=0, le=18, description="Number of decision elements present")
    weak: int = Field(..., ge=0, le=18, description="Number of decision elements weak/fragmented")
    missing: int = Field(..., ge=0, le=18, description="Number of decision elements missing")
    total: int = Field(..., ge=12, le=18, description="Total number of decision elements analyzed")


class AuditResult(BaseModel):
    """
    AI Visibility Sales Report (Stages 1–5)
    This is a SALES document, not a technical audit.
    """
    stage_1_ai_visibility: Stage1AIVisibility
    ai_interpretation: AIInterpretation
    decision_readiness_audit: List[DecisionReadinessItem] = Field(..., min_length=12, max_length=18, description="12-18 decision elements (MUST be personalized from scraping, granular audit)")
    decision_coverage_score: DecisionCoverageScore = Field(..., description="Summary of decision element coverage")
    recommendation_verdict: Optional[Dict[str, str]] = Field(default=None, description="Verdict: blocked/limited/allowed + verdict_statement")
    ai_requirements_before: List[AIRequirementBefore] = Field(..., min_length=10, max_length=20, description="10-20 AI requirements (BEFORE state - what is missing)")
    ai_requirements_after: List[AIRequirementAfter] = Field(..., min_length=10, max_length=20, description="10-20 AI requirements (AFTER state - what must be built)")
    stage_2_why_ai_chooses_others: List[Stage2Reason] = Field(..., max_length=5, description="Up to 5 reasons (LEGACY, use decision_readiness_audit instead)")
    stage_3_what_ai_needs: List[Stage3Need] = Field(..., max_length=8, description="Content types needed (LEGACY, use ai_requirements instead)")
    stage_4_packages: Stage4Packages
    stage_5_business_impact: Stage5BusinessImpact
    appendix: Appendix
    evidence_layer: Optional[EvidenceLayer] = Field(default=None, description="Deterministic evidence derived from scraping (not LLM-generated)")
    
    class Config:
        extra = "forbid"  # Crash on unknown fields - prevents silent data loss


# =============================================================================
# STAGE B: Action Plan Builder Schema (Pages + Outlines + Impact Forecast)
# =============================================================================

class RecommendedPage(BaseModel):
    """Recommended new or restructured page for LLM visibility"""
    page_title: str = Field(..., description="Page title")
    slug_suggestion: str = Field(..., description="URL slug suggestion, e.g. /services/concrete-repair")
    goal_for_llms: str = Field(..., description="What this page helps LLMs understand/recommend")
    content_unit_type: Literal["service_page", "entity_page", "comparison_page", "trust_page", "faq_page", "hub_page"] = Field(
        ..., description="Type of content unit for LLM coverage"
    )
    counts_toward_coverage: bool = Field(default=True, description="Whether this page counts toward LLM coverage metrics")
    must_have_blocks: List[str] = Field(..., max_length=8, description="Content blocks that must be on this page")
    outline: List[str] = Field(..., max_length=10, description="Section outline for the page")
    example_snippet_for_citation: str = Field(..., description="Example text that LLMs could quote directly")


class SitewideBlock(BaseModel):
    """Sitewide content block to add across the site"""
    block_name: str
    where_to_place: str = Field(..., description="Where on the site this block should appear")
    why_it_helps_llms: str = Field(..., description="How this improves LLM citations/recommendations")
    example_copy: str = Field(..., description="Example text for this block")


class CoverageLevel(BaseModel):
    """Definition of an LLM Coverage level tier"""
    level_name: Literal["baseline", "recommended", "authority"] = Field(..., description="Coverage tier name")
    page_count_range: str = Field(..., description="Range of pages needed, e.g. '4-6 pages'")
    typical_content_units_range: str = Field(
        ...,
        description="Typical range of LLM-focused content units (capacity language), e.g. '5-7 content units'",
    )
    page_types: List[str] = Field(..., description="Types of pages included at this level")
    llm_capability_unlocked: str = Field(..., description="What AI can do at this level: understand → compare → recommend")
    what_ai_can_do_at_this_level: str = Field(
        ...,
        description="Plain-language capability framing (Baseline=understands/describes; Recommended=compares/suggests; Authority=proactively recommends/cites)",
    )
    who_this_level_is_for: str = Field(
        ...,
        description="Who this level is for (team capacity / budget / goals), aligned to packaging tiers",
    )
    expected_shift: str = Field(..., description="Qualitative description of expected change (no traffic numbers)")


class LLMCoverageLevels(BaseModel):
    """Three-tier LLM Coverage framework"""
    baseline: CoverageLevel = Field(..., description="Minimum viable coverage for basic AI understanding")
    recommended: CoverageLevel = Field(..., description="Recommended coverage for AI comparison capability")
    authority: CoverageLevel = Field(..., description="Full coverage for confident AI recommendations")
    current_assessment: str = Field(..., description="Where the site currently stands")


class ImpactForecast(BaseModel):
    """
    Impact forecast tied to LLM Coverage levels
    NO traffic numbers - qualitative shifts only
    """
    baseline_impact: str = Field(..., description="Impact at Baseline coverage - low confidence")
    recommended_impact: str = Field(..., description="Impact at Recommended coverage - medium confidence") 
    authority_impact: str = Field(..., description="Impact at Authority coverage - high confidence")
    why_coverage_matters: str = Field(..., description="Explanation of why more coverage = higher confidence")
    key_unlocks: List[str] = Field(..., max_length=4, description="What each coverage level unlocks for AI")


class ContentSummary(BaseModel):
    """Summary of content work required"""
    total_content_units: str = Field(..., description="Range of content units, e.g. '8-12 LLM-focused content units'")
    breakdown_by_type: Dict[str, int] = Field(..., description="Count by content unit type")
    estimated_coverage_level: Literal["baseline", "recommended", "authority"] = Field(
        ..., description="Coverage level this plan achieves"
    )


CoverageAssessment = Literal[
    "partial baseline",
    "baseline",
    "partial recommended",
    "recommended",
    "partial authority",
    "authority",
]


class GrowthPlanCoverageSummary(BaseModel):
    """Decision summary: current coverage → plan coverage and remaining scope to next tier."""
    current_coverage_level: CoverageAssessment = Field(
        ...,
        description="Estimated current coverage level before executing the plan (use 'partial X' when between tiers)",
    )
    coverage_after_plan: Literal["baseline", "recommended", "authority"] = Field(
        ...,
        description="Coverage level achieved after executing this plan",
    )
    content_units_needed_for_next_level: str = Field(
        ...,
        description="Approx additional LLM-focused content units needed to reach the next tier, e.g. '5–7' or 'N/A (already at Authority)'",
    )


class MeasurementPlan(BaseModel):
    """How to measure LLM visibility improvements (NOT SEO metrics)"""
    what_to_track: List[str] = Field(..., description="Metrics to track (LLM mentions, citations, brand association)")
    simple_tests: List[str] = Field(..., description="Simple tests to run (e.g., 'Ask ChatGPT about X')")


class ActionPlanResult(BaseModel):
    """
    Stage B Output: Action Plan for LLM Visibility
    Converts audit findings into practical website upgrade plan with clear coverage tiers
    """
    recommended_pages: List[RecommendedPage] = Field(..., max_length=8, description="Pages to add or restructure")
    sitewide_blocks_to_add: List[SitewideBlock] = Field(..., max_length=6, description="Blocks to add across the site")
    coverage_levels: LLMCoverageLevels = Field(..., description="Three-tier LLM coverage framework")
    content_summary: ContentSummary = Field(..., description="Summary of content work required")
    growth_plan_summary: GrowthPlanCoverageSummary = Field(
        ...,
        description="Mandatory decision summary tying coverage levels to growth plan and execution scope",
    )
    impact_forecast: ImpactForecast = Field(..., description="Impact forecast tied to coverage levels")
    measurement_plan: MeasurementPlan
