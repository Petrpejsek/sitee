"""API routes for audit operations"""
from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import AuditJob, AuditOutput, AuditOutputSnapshot, AuditAccessState
from app.services.report_generator import ReportGenerator
from app.services.access_control import AccessControlService
from app.api.auth import get_current_user_id
from app.schemas import (
    AuditCreateRequest,
    AuditCreateResponse,
    AuditJobResponse,
)
import os
from copy import deepcopy

router = APIRouter()


# =========================================================================
# PAYWALL DATA FILTERING HELPERS
# These functions filter audit data based on access state.
# Backend is SINGLE SOURCE OF TRUTH - frontend just renders what it gets.
# =========================================================================

def _filter_preview_audit_data(audit_data: dict) -> dict:
    """
    PREVIEW (anonymous): Minimal data only
    - AI visibility score
    - 1-2 sentence high-level summary
    - NO problem details, NO recommendations
    """
    if not isinstance(audit_data, dict):
        return {}
    
    # Extract only the absolute minimum
    stage1 = audit_data.get("stage_1_ai_visibility") or {}
    ai_interp = audit_data.get("ai_interpretation") or {}
    
    return {
        "stage_1_ai_visibility": {
            "executive_summary": stage1.get("executive_summary"),
            "scores": stage1.get("scores"),
            # No detailed findings
        },
        "ai_interpretation": {
            "summary": ai_interp.get("summary"),
            # No detailed interpretation
        },
        # No other sections
    }


def _filter_locked_audit_data(audit_data: dict) -> dict:
    """
    LOCKED (registered but not paid): Teaser data only
    - AI visibility score
    - Top 3-5 problems (NAMES ONLY, no details or fixes)
    - Section titles with 1-line hints
    - NO detailed checklists, recommendations, steps, or "how to fix"
    
    User should think: "I see it's broken, but I need to unlock to know what to do"
    """
    if not isinstance(audit_data, dict):
        return {}
    
    stage1 = audit_data.get("stage_1_ai_visibility") or {}
    ai_interp = audit_data.get("ai_interpretation") or {}
    stage2 = audit_data.get("stage_2_company_intel") or {}
    stage3 = audit_data.get("stage_3_decision_audit") or {}
    
    # Filter top_gaps to show only titles (no recommendations)
    top_gaps = stage1.get("top_gaps") or []
    filtered_gaps = []
    for gap in top_gaps[:5]:  # Max 5 gaps
        if isinstance(gap, dict):
            filtered_gaps.append({
                "title": gap.get("title") or gap.get("gap") or "Issue detected",
                "severity": gap.get("severity", "medium"),
                "locked": True,
                "teaser": "Unlock to see detailed analysis and fix",
                # NO: recommendation, details, steps, explanation
            })
    
    # Filter visibility risks to show only high-level
    risks = stage1.get("llm_visibility_risks") or []
    filtered_risks = []
    for risk in risks[:3]:  # Max 3 risks
        if isinstance(risk, dict):
            filtered_risks.append({
                "title": risk.get("title") or risk.get("risk") or "Risk identified",
                "severity": risk.get("severity", "medium"),
                "locked": True,
                "teaser": "Unlock to see impact and recommendations",
                # NO: details, impact, recommendation
            })
    
    # Filter decision audit - show category names only
    decision_audit = stage3.get("decision_audit") or []
    filtered_decision = []
    for item in decision_audit:
        if isinstance(item, dict):
            filtered_decision.append({
                "requirement": item.get("requirement", "Requirement"),
                "status": item.get("status", "unknown"),
                "locked": True,
                # NO: finding, recommendation, source_evidence
            })
    
    # Build locked payload
    return {
        "stage_1_ai_visibility": {
            "executive_summary": stage1.get("executive_summary"),
            "scores": stage1.get("scores"),
            "top_gaps": filtered_gaps,
            "llm_visibility_risks": filtered_risks,
            # Section hints
            "section_hints": {
                "gaps": f"{len(top_gaps)} issues found that hurt your AI visibility",
                "risks": f"{len(risks)} risks identified affecting LLM recommendations",
            },
            # NO: detailed checklists, full explanations
        },
        "ai_interpretation": {
            "summary": ai_interp.get("summary"),
            "locked": True,
            # NO: detailed interpretation, market analysis
        },
        "stage_2_company_intel": {
            "company_name": stage2.get("company_name"),
            "primary_offer": stage2.get("primary_offer"),
            "locked": True,
            "teaser": "Full company analysis available after unlock",
            # NO: detailed intel, competitor analysis
        },
        "stage_3_decision_audit": {
            "decision_audit": filtered_decision,
            "locked": True,
            "total_requirements": len(decision_audit),
            "passing_count": len([d for d in decision_audit if isinstance(d, dict) and d.get("status") == "present"]),
            "teaser": "Detailed recommendations available after unlock",
            # NO: detailed requirements, sources, fixes
        },
        # NO stage_4_packages (Section 6) - completely removed
        "_locked_notice": "Full audit details are locked. Unlock to see complete analysis and recommendations.",
    }


@router.post("/audit", response_model=AuditCreateResponse)
async def create_audit(
    request: AuditCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new audit job - only domain required, everything else extracted from scraping"""
    
    # Create new job with server-side defaults
    # locale, competitors, company fields are NOT from user input
    job = AuditJob(
        target_domain=request.target_domain,
        competitor_domains=[],  # Empty - not used, will be added in future
        locale="en-US",  # Server-side constant, never from user input
        company_description=None,  # Will be extracted from scraping
        products_services=None,  # Will be extracted from scraping
        status="pending",
        progress_percent=0,
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    return AuditCreateResponse(
        id=job.id,
        status=job.status,
        message="Audit job created successfully. Worker will process it shortly.",
    )


@router.get("/audit/{job_id}", response_model=AuditJobResponse)
async def get_audit(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get audit job status and results"""
    
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")
    
    return AuditJobResponse.model_validate(job)


@router.get("/audit/{job_id}/pdf")
async def download_pdf(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download PDF report from DB"""
    
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Audit not yet completed")
    
    # Get output from DB
    output_result = await db.execute(
        select(AuditOutput).where(AuditOutput.audit_job_id == job_id)
    )
    output = output_result.scalar_one_or_none()
    
    if not output or not output.pdf_path:
        raise HTTPException(status_code=404, detail="PDF report not found in database")
    
    if not os.path.exists(output.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    
    return FileResponse(
        output.pdf_path,
        media_type="application/pdf",
        filename=f"llm-audit-{job.target_domain}-{job.id}.pdf",
    )


@router.get("/audit/{job_id}/json")
async def download_json(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Download JSON audit result from DB
    Returns combined payload with Stage A (audit) and Stage B (action_plan)
    """
    
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Audit not yet completed")
    
    # Get output from DB
    output_result = await db.execute(
        select(AuditOutput).where(AuditOutput.audit_job_id == job_id)
    )
    output = output_result.scalar_one_or_none()
    
    if not output or not output.audit_json:
        raise HTTPException(status_code=404, detail="JSON audit result not found in database")
    
    # Return combined payload with both Stage A and Stage B
    combined_payload = {
        "meta": {
            "job_id": str(job.id),
            "domain": job.target_domain,
            "locale": job.locale,
            "generated_at": output.created_at.isoformat() if output.created_at else None,
            "model": output.model,
            "pipeline_version": "2.0",  # 2-stage pipeline
        },
        "core_audit": output.audit_json,  # Stage A
        "action_plan": output.action_plan_json,  # Stage B (can be None for old audits)
        "sampled_urls": output.sampled_urls,
    }
    
    return JSONResponse(
        content=combined_payload,
        headers={
            "Content-Disposition": f"attachment; filename=llm-audit-{job.target_domain}-{job.id}.json"
        },
    )


@router.get("/audit/{job_id}/html")
async def preview_html(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Preview HTML report from DB"""
    
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Audit not yet completed")
    
    # Get output from DB
    output_result = await db.execute(
        select(AuditOutput).where(AuditOutput.audit_job_id == job_id)
    )
    output = output_result.scalar_one_or_none()
    
    if not output or not output.report_html:
        raise HTTPException(status_code=404, detail="HTML report not found in database")
    
    return HTMLResponse(content=output.report_html)


@router.get("/audit/{job_id}/report")
async def get_report_view_model(
    job_id: UUID,
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    URL-first dashboard payload with access control.
    
    Filters content based on user authentication and payment status.
    Section 6 is ONLY returned if audit is unlocked.
    """
    result = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Audit not yet completed")

    output_result = await db.execute(select(AuditOutput).where(AuditOutput.audit_job_id == job_id))
    output = output_result.scalar_one_or_none()

    if not output or not output.audit_json:
        raise HTTPException(status_code=404, detail="Audit output not found")

    # Determine access state based on user and payment status
    access_control = AccessControlService(db)
    access_state = await access_control.get_audit_access_state(user_id, job_id)
    
    # Deep copy audit data to avoid modifying original
    from copy import deepcopy
    audit_data = deepcopy(output.audit_json)
    action_plan_data = deepcopy(output.action_plan_json) if output.action_plan_json else None
    
    # =========================================================================
    # ACCESS CONTROL: Filter content based on access state
    # Backend is SINGLE SOURCE OF TRUTH - frontend just renders what it gets
    # =========================================================================
    
    if access_state == AuditAccessState.UNLOCKED:
        # Full access - return everything as-is
        pass
        
    elif access_state == AuditAccessState.LOCKED:
        # LOCKED: Show teaser only - no detailed recommendations or action plans
        # User sees "what's wrong" but NOT "how to fix it"
        audit_data = _filter_locked_audit_data(audit_data)
        action_plan_data = None  # No action plan for locked users
        
    elif access_state == AuditAccessState.PREVIEW:
        # PREVIEW (anonymous): Minimal data - just score and high-level summary
        audit_data = _filter_preview_audit_data(audit_data)
        action_plan_data = None

    generator = ReportGenerator(db)
    payload = generator.build_report_view_model(
        job_id=str(job.id),
        domain=job.target_domain,
        locale=job.locale,
        generated_at=output.created_at.isoformat() if output.created_at else None,
        model=output.model,
        audit_data=audit_data,
        action_plan_data=action_plan_data,
        sampled_urls=output.sampled_urls,
    )

    # Retention: change since last run (if snapshot exists)
    snap_result = await db.execute(
        select(AuditOutputSnapshot)
        .where(AuditOutputSnapshot.audit_job_id == job_id)
        .order_by(AuditOutputSnapshot.created_at.desc())
        .limit(1)
    )
    prev = snap_result.scalar_one_or_none()
    if prev:
        try:
            cur_scores = (output.audit_json or {}).get("scores") or {}
            prev_scores = (prev.audit_json or {}).get("scores") or {}
            cur_gaps = (output.audit_json or {}).get("top_gaps") or []
            prev_gaps = (prev.audit_json or {}).get("top_gaps") or []
            cur_risks = (output.audit_json or {}).get("llm_visibility_risks") or []
            prev_risks = (prev.audit_json or {}).get("llm_visibility_risks") or []

            def _int_or_none(x):
                try:
                    return int(x)
                except Exception:
                    return None

            cur_rec = _int_or_none(cur_scores.get("recommendability"))
            prev_rec = _int_or_none(prev_scores.get("recommendability"))
            cur_cl = _int_or_none(cur_scores.get("clarity_of_offering"))
            prev_cl = _int_or_none(prev_scores.get("clarity_of_offering"))
            cur_comp = _int_or_none(cur_scores.get("comparability"))
            prev_comp = _int_or_none(prev_scores.get("comparability"))

            payload["meta"]["previous_generated_at"] = prev.created_at.isoformat() if prev.created_at else None
            payload["meta"]["delta"] = {
                "recommendability": (cur_rec - prev_rec) if cur_rec is not None and prev_rec is not None else None,
                "clarity_of_offering": (cur_cl - prev_cl) if cur_cl is not None and prev_cl is not None else None,
                "comparability": (cur_comp - prev_comp) if cur_comp is not None and prev_comp is not None else None,
                "gaps_total": (len(cur_gaps) - len(prev_gaps)) if isinstance(cur_gaps, list) and isinstance(prev_gaps, list) else None,
                "risks_total": (len(cur_risks) - len(prev_risks)) if isinstance(cur_risks, list) and isinstance(prev_risks, list) else None,
            }
        except Exception:
            payload["meta"]["previous_generated_at"] = prev.created_at.isoformat() if prev.created_at else None
            payload["meta"]["delta"] = {
                "recommendability": None,
                "clarity_of_offering": None,
                "comparability": None,
                "gaps_total": None,
                "risks_total": None,
            }

    # Access control metadata for frontend
    locked_sections = access_control.get_locked_sections(access_state)
    
    # Get user info if authenticated
    has_subscription = False
    has_paid_audit = False
    if user_id:
        has_subscription = await access_control.has_active_subscription(user_id)
        has_paid_audit = await access_control.has_paid_for_audit(user_id, job_id)
    
    payload["meta"]["access_state"] = access_state.value
    payload["meta"]["locked_sections"] = locked_sections
    payload["meta"]["user_authenticated"] = user_id is not None
    payload["meta"]["has_subscription"] = has_subscription
    payload["meta"]["has_paid_audit"] = has_paid_audit
    payload["meta"]["can_unlock"] = user_id is not None and access_state == AuditAccessState.LOCKED

    return JSONResponse(content=payload)


@router.post("/audit/{job_id}/rerun")
async def rerun_audit(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Manual re-analysis entrypoint (alias of retry for retention)."""
    result = await db.execute(select(AuditJob).where(AuditJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if job.status not in ["failed", "completed"]:
        raise HTTPException(status_code=400, detail="Can only re-run failed or completed jobs")

    job.status = "pending"
    job.error_message = None
    job.progress_percent = 0
    job.current_stage = None
    job.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Job queued for re-run", "job_id": str(job.id), "status": "pending"}


@router.post("/audit/{job_id}/retry")
async def retry_audit(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed audit job"""
    
    result = await db.execute(
        select(AuditJob).where(AuditJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")
    
    if job.status not in ["failed", "completed"]:
        raise HTTPException(status_code=400, detail="Can only retry failed or completed jobs")
    
    # Reset job status
    job.status = "pending"
    job.error_message = None
    job.progress_percent = 0
    job.current_stage = None
    job.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Job queued for retry", "job_id": str(job.id), "status": "pending"}
