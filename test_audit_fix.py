#!/usr/bin/env python3
"""
Quick test script to verify audit pipeline fix
Run: python3 test_audit_fix.py
"""
import asyncio
import json
from datetime import datetime
from app.schemas import (
    AuditResult,
    DecisionReadinessItem,
    AIRequirementBefore,
    AIRequirementAfter,
    DecisionCoverageScore
)

def test_schema_compatibility():
    """Test that new schema accepts correct data structure"""
    print("="*80)
    print("TESTING SCHEMA COMPATIBILITY")
    print("="*80)
    
    # Simulate LLM output with new structure
    mock_llm_output = {
        "stage_1_ai_visibility": {
            "chatgpt_visibility_percent": 15,
            "chatgpt_label": "Poor",
            "gemini_visibility_percent": 10,
            "gemini_label": "Poor",
            "perplexity_visibility_percent": 12,
            "perplexity_label": "Poor",
            "hard_sentence": "AI models usually recommend competitors instead of this business."
        },
        "ai_interpretation": {
            "summary": "Based on analyzed content, AI sees this as a generic business with unclear differentiation.",
            "confidence": "shallow",
            "based_on_pages": 5,
            "detected_signals": ["Brand name", "Generic service keywords"],
            "missing_elements": [
                {
                    "key": "service_differentiation",
                    "label": "No clear service differentiation",
                    "impact": "AI cannot explain how you differ from alternatives",
                    "severity": "critical"
                },
                {
                    "key": "pricing_structure",
                    "label": "No pricing structure",
                    "impact": "AI cannot compare value",
                    "severity": "critical"
                },
                {
                    "key": "decision_context",
                    "label": "No decision context",
                    "impact": "AI cannot guide users",
                    "severity": "critical"
                },
                {
                    "key": "comparison_content",
                    "label": "No comparison content",
                    "impact": "AI cannot position you",
                    "severity": "supporting"
                }
            ]
        },
        "decision_readiness_audit": [
            {
                "element_name": "Structured Service Pages",
                "status": "missing",
                "what_ai_requires": "LLMs require structured, quotable service explanations.",
                "what_we_found": "Service information not clearly structured for AI citation.",
                "impact_on_recommendation": "AI cannot confidently explain offerings to users.",
                "evidence_refs": [0, 1]
            },
            {
                "element_name": "Pricing & Value Information",
                "status": "missing",
                "what_ai_requires": "AI systems need explicit pricing comparisons.",
                "what_we_found": "No pricing detected.",
                "impact_on_recommendation": "AI cannot compare value.",
                "evidence_refs": []
            },
            {
                "element_name": "FAQ Content",
                "status": "weak",
                "what_ai_requires": "LLMs need structured Q&A.",
                "what_we_found": "No FAQ detected.",
                "impact_on_recommendation": "AI lacks quotable answers.",
                "evidence_refs": []
            },
            {
                "element_name": "Decision Guidance",
                "status": "missing",
                "what_ai_requires": "AI needs audience fit statements.",
                "what_we_found": "No guidance detected.",
                "impact_on_recommendation": "AI cannot match to queries.",
                "evidence_refs": []
            },
            {
                "element_name": "Comparison Content",
                "status": "missing",
                "what_ai_requires": "AI needs competitive positioning.",
                "what_we_found": "No comparison content.",
                "impact_on_recommendation": "AI defaults to competitors.",
                "evidence_refs": []
            },
            {
                "element_name": "Entity Signals",
                "status": "weak",
                "what_ai_requires": "LLMs need trust signals.",
                "what_we_found": "Minimal signals detected.",
                "impact_on_recommendation": "Lower confidence.",
                "evidence_refs": []
            },
            {
                "element_name": "Operational Clarity",
                "status": "weak",
                "what_ai_requires": "AI needs process details.",
                "what_we_found": "Not structured.",
                "impact_on_recommendation": "Cannot provide details.",
                "evidence_refs": []
            },
            {
                "element_name": "Authority Content",
                "status": "missing",
                "what_ai_requires": "AI needs educational content.",
                "what_we_found": "No guides detected.",
                "impact_on_recommendation": "Lower perceived expertise.",
                "evidence_refs": []
            }
        ],
        "decision_coverage_score": {
            "present": 0,
            "weak": 3,
            "missing": 5,
            "total": 8
        },
        "recommendation_verdict": {
            "verdict": "blocked",
            "verdict_statement": "AI systems cannot confidently recommend this business due to missing decision structure."
        },
        "ai_requirements_before": [
            {
                "requirement_name": "Explicit service definitions",
                "category": "Decision Clarity",
                "why_ai_needs_this": "AI needs clear scope to explain offerings.",
                "current_status": "not_found",
                "impact_if_missing": "AI cannot describe what you offer."
            },
            {
                "requirement_name": "Pricing transparency",
                "category": "Comparability",
                "why_ai_needs_this": "AI needs pricing to compare value.",
                "current_status": "not_found",
                "impact_if_missing": "AI defaults to competitors with pricing."
            },
            {
                "requirement_name": "Decision guidance",
                "category": "Decision Clarity",
                "why_ai_needs_this": "AI needs fit statements.",
                "current_status": "not_found",
                "impact_if_missing": "AI cannot match to needs."
            },
            {
                "requirement_name": "FAQ content",
                "category": "Decision Clarity",
                "why_ai_needs_this": "AI needs Q&A structure.",
                "current_status": "not_found",
                "impact_if_missing": "AI lacks quotable answers."
            },
            {
                "requirement_name": "Testimonials",
                "category": "Trust & Authority",
                "why_ai_needs_this": "AI needs proof.",
                "current_status": "weak",
                "impact_if_missing": "Lower trust."
            },
            {
                "requirement_name": "Comparison content",
                "category": "Comparability",
                "why_ai_needs_this": "AI needs positioning.",
                "current_status": "not_found",
                "impact_if_missing": "Cannot differentiate."
            },
            {
                "requirement_name": "Entity signals",
                "category": "Entity Understanding",
                "why_ai_needs_this": "AI needs structured entity data.",
                "current_status": "weak",
                "impact_if_missing": "Weak entity treatment."
            },
            {
                "requirement_name": "Operational clarity",
                "category": "Risk Reduction",
                "why_ai_needs_this": "AI needs process details.",
                "current_status": "weak",
                "impact_if_missing": "Cannot explain process."
            },
            {
                "requirement_name": "Authority content",
                "category": "Trust & Authority",
                "why_ai_needs_this": "AI needs expertise signals.",
                "current_status": "not_found",
                "impact_if_missing": "Lower credibility."
            },
            {
                "requirement_name": "Risk reduction",
                "category": "Risk Reduction",
                "why_ai_needs_this": "AI needs guarantees.",
                "current_status": "not_found",
                "impact_if_missing": "Higher perceived risk."
            }
        ],
        "ai_requirements_after": [
            {
                "requirement_name": "Explicit service definitions",
                "category": "Decision Clarity",
                "what_must_be_built": "Build structured service pages.",
                "ai_outcome_unlocked": "AI can explain offerings."
            },
            {
                "requirement_name": "Pricing transparency",
                "category": "Comparability",
                "what_must_be_built": "Add pricing tiers.",
                "ai_outcome_unlocked": "AI can compare value."
            },
            {
                "requirement_name": "Decision guidance",
                "category": "Decision Clarity",
                "what_must_be_built": "Create fit sections.",
                "ai_outcome_unlocked": "AI can match to needs."
            },
            {
                "requirement_name": "FAQ content",
                "category": "Decision Clarity",
                "what_must_be_built": "Build FAQ sections.",
                "ai_outcome_unlocked": "AI can quote answers."
            },
            {
                "requirement_name": "Testimonials",
                "category": "Trust & Authority",
                "what_must_be_built": "Add testimonials with results.",
                "ai_outcome_unlocked": "AI gains proof."
            },
            {
                "requirement_name": "Comparison content",
                "category": "Comparability",
                "what_must_be_built": "Build vs pages.",
                "ai_outcome_unlocked": "AI can position."
            },
            {
                "requirement_name": "Entity signals",
                "category": "Entity Understanding",
                "what_must_be_built": "Strengthen About pages.",
                "ai_outcome_unlocked": "AI treats as credible entity."
            },
            {
                "requirement_name": "Operational clarity",
                "category": "Risk Reduction",
                "what_must_be_built": "Add process info.",
                "ai_outcome_unlocked": "AI can explain process."
            },
            {
                "requirement_name": "Authority content",
                "category": "Trust & Authority",
                "what_must_be_built": "Build guides.",
                "ai_outcome_unlocked": "AI sees expertise."
            },
            {
                "requirement_name": "Risk reduction",
                "category": "Risk Reduction",
                "what_must_be_built": "Add guarantees.",
                "ai_outcome_unlocked": "Lower perceived risk."
            }
        ],
        "stage_2_why_ai_chooses_others": [
            {
                "how_llms_decide": "LLMs prefer sources with structured information.",
                "what_we_found_on_your_site": "Information is scattered.",
                "what_ai_does_instead": "AI recommends competitors.",
                "what_must_be_built": "Build structured pages.",
                "evidence_refs": [0]
            }
        ],
        "stage_3_what_ai_needs": [
            {
                "content_type": "Service pages",
                "what_it_unlocks": "AI understanding",
                "status": "not_found",
                "what_we_saw": "No structured service pages",
                "impact": "AI cannot explain",
                "evidence_refs": []
            }
        ],
        "stage_4_packages": {
            "ai_entry_10_pages": {
                "package_name": "AI Entry Package",
                "pages": 10,
                "purpose": "Basic AI understanding",
                "messaging": "Get AI to understand who you are",
                "what_ai_can_do": ["Understand", "Describe"],
                "ties_to_findings": "Fixes missing structure",
                "pages_to_build": ["How X Works", "Pricing"]
            },
            "ai_recommendation_30_pages": {
                "package_name": "AI Recommendation Package",
                "pages": 30,
                "purpose": "AI comparison capability",
                "messaging": "Get AI to recommend you",
                "what_ai_can_do": ["Compare", "Suggest"],
                "ties_to_findings": "Fixes missing comparison",
                "pages_to_build": ["How X Works", "Pricing", "vs Alternatives"]
            },
            "ai_authority_100_pages": {
                "package_name": "AI Authority Package",
                "pages": 100,
                "purpose": "AI confident recommendations",
                "messaging": "Get AI to prefer you",
                "what_ai_can_do": ["Prefer", "Cite"],
                "ties_to_findings": "Fixes everything",
                "pages_to_build": ["Full coverage"]
            }
        },
        "stage_5_business_impact": {
            "what_staying_invisible_costs": "Lost opportunities",
            "why_ai_visibility_compounds": "Early movers win",
            "why_waiting_makes_this_worse": "Competitors gain ground",
            "competitor_preference_proof": "Competitors have structure",
            "recommended_option": "30-page AI Recommendation package",
            "closing_line": "Based on this, the recommended option is the 30-page AI Recommendation package.",
            "neutrality_block": "This audit is platform-agnostic.",
            "our_offer_block": "We can deliver Wave 1 in fixed scope."
        },
        "appendix": {
            "sampled_urls": ["https://example.com"],
            "data_limitations": "Analysis based on 5 pages",
            "pages_analyzed_target": 5,
            "pages_analyzed_competitors": 0
        }
    }
    
    # Test validation
    try:
        validated = AuditResult(**mock_llm_output)
        print("\n✅ SCHEMA VALIDATION PASSED")
        print(f"\n📊 Decision Readiness: {len(validated.decision_readiness_audit)} elements")
        print(f"📊 Decision Coverage: {validated.decision_coverage_score.present} present, {validated.decision_coverage_score.weak} weak, {validated.decision_coverage_score.missing} missing")
        print(f"📊 AI Requirements (BEFORE): {len(validated.ai_requirements_before)} items")
        print(f"📊 AI Requirements (AFTER): {len(validated.ai_requirements_after)} items")
        print(f"\n🎯 Recommendation Verdict: {validated.recommendation_verdict.get('verdict', 'N/A')}")
        print("\n" + "="*80)
        return True
    except Exception as e:
        print(f"\n❌ SCHEMA VALIDATION FAILED")
        print(f"Error: {e}")
        print("\n" + "="*80)
        return False

def test_forbid_unknown_fields():
    """Test that extra='forbid' rejects unknown fields"""
    print("\n" + "="*80)
    print("TESTING extra='forbid' - SHOULD REJECT UNKNOWN FIELDS")
    print("="*80)
    
    # This should FAIL because ai_requirements is not in schema
    mock_bad_output = {
        "stage_1_ai_visibility": {
            "chatgpt_visibility_percent": 15,
            "chatgpt_label": "Poor",
            "gemini_visibility_percent": 10,
            "gemini_label": "Poor",
            "perplexity_visibility_percent": 12,
            "perplexity_label": "Poor",
            "hard_sentence": "Test"
        },
        "ai_interpretation": {
            "summary": "Test",
            "confidence": "shallow",
            "based_on_pages": 5,
            "detected_signals": ["Test"],
            "missing_elements": [
                {"key": "test", "label": "Test", "impact": "Test", "severity": "critical"},
                {"key": "test2", "label": "Test2", "impact": "Test2", "severity": "critical"},
                {"key": "test3", "label": "Test3", "impact": "Test3", "severity": "critical"},
                {"key": "test4", "label": "Test4", "impact": "Test4", "severity": "critical"}
            ]
        },
        "decision_readiness_audit": [],
        "decision_coverage_score": {"present": 0, "weak": 0, "missing": 0, "total": 0},
        "ai_requirements_before": [],
        "ai_requirements_after": [],
        "ai_requirements": [{"test": "THIS SHOULD BE REJECTED"}],  # ← OLD FIELD
        "stage_2_why_ai_chooses_others": [],
        "stage_3_what_ai_needs": [],
        "stage_4_packages": {
            "ai_entry_10_pages": {"package_name": "Test", "pages": 10, "purpose": "Test", "messaging": "Test", "what_ai_can_do": ["Test"], "ties_to_findings": "Test"},
            "ai_recommendation_30_pages": {"package_name": "Test", "pages": 30, "purpose": "Test", "messaging": "Test", "what_ai_can_do": ["Test"], "ties_to_findings": "Test"},
            "ai_authority_100_pages": {"package_name": "Test", "pages": 100, "purpose": "Test", "messaging": "Test", "what_ai_can_do": ["Test"], "ties_to_findings": "Test"}
        },
        "stage_5_business_impact": {
            "what_staying_invisible_costs": "Test",
            "why_ai_visibility_compounds": "Test",
            "why_waiting_makes_this_worse": "Test",
            "competitor_preference_proof": "Test",
            "recommended_option": "30-page AI Recommendation package",
            "closing_line": "Test"
        },
        "appendix": {
            "sampled_urls": [],
            "data_limitations": "Test",
            "pages_analyzed_target": 0,
            "pages_analyzed_competitors": 0
        }
    }
    
    try:
        validated = AuditResult(**mock_bad_output)
        print("❌ TEST FAILED - Schema accepted unknown field 'ai_requirements'")
        print("extra='forbid' is NOT working!")
        return False
    except Exception as e:
        if "ai_requirements" in str(e) or "Extra inputs" in str(e):
            print("✅ TEST PASSED - Schema correctly rejected unknown field")
            print(f"Error (expected): {e}")
            return True
        else:
            print(f"❓ TEST UNCLEAR - Got different error: {e}")
            return False

if __name__ == "__main__":
    print("\n🧪 AUDIT PIPELINE FIX - SCHEMA TEST")
    print("="*80)
    
    test1 = test_schema_compatibility()
    test2 = test_forbid_unknown_fields()
    
    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    if test1 and test2:
        print("✅ ALL TESTS PASSED - Schema is correct!")
        print("\n📋 NEXT STEPS:")
        print("1. Spusť backend: ./dev.sh start (nebo restart)")
        print("2. Vytvoř nový audit přes UI")
        print("3. Sleduj logy: tail -f logs/*.log")
        print("4. Ověř, že Section 03 a 04 obsahují data")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    print("="*80)
