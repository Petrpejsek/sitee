"""
Report generation service (HTML → PDF)
Combines Stage A (Core Audit) + Stage B (Action Plan) into unified report
"""
import asyncio
import os
import uuid
import re
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import get_settings
from app.models import AuditJob, AuditOutput, AuditOutputSnapshot

settings = get_settings()


class ReportGenerator:
    """Generate HTML and PDF reports from audit results"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

    def _default_coverage_levels(self) -> Dict[str, Any]:
        """
        Deterministic fallback so 'LLM Coverage Levels' is NEVER empty (older audits, partial Stage B payloads).
        Uses capacity language aligned to packaging tiers.
        """
        return {
            "baseline": {
                "level_name": "baseline",
                "page_count_range": "3–6 pages",
                # UX guarantee directive: MUST always be filled with fixed ranges
                "typical_content_units_range": "4–6 content units",
                "page_types": ["home", "service/product", "about/entity", "contact"],
                "llm_capability_unlocked": "Understand → describe (basic)",
                "what_ai_can_do_at_this_level": "AI understands the offering and can describe it, but recommendations are cautious and inconsistent.",
                "who_this_level_is_for": "Teams starting from low AI clarity who need a minimum viable foundation for AI understanding.",
                "expected_shift": "More consistent basic descriptions and safer citations, but limited comparisons.",
            },
            "recommended": {
                "level_name": "recommended",
                "page_count_range": "7–12 pages",
                # UX guarantee directive: MUST always be filled with fixed ranges
                "typical_content_units_range": "8–12 content units",
                "page_types": ["service/product depth", "FAQ", "trust/proof", "use-cases", "pricing transparency"],
                "llm_capability_unlocked": "Compare → suggest (reliable)",
                "what_ai_can_do_at_this_level": "AI compares you with alternatives and can suggest you in shortlists with clearer reasons.",
                "who_this_level_is_for": "Brands that want reliable AI comparisons and stronger recommendation confidence with manageable scope.",
                "expected_shift": "AI answers become more specific, quotable, and comparison-ready.",
            },
            "authority": {
                "level_name": "authority",
                "page_count_range": "13–20 pages",
                # UX guarantee directive: MUST always be filled with fixed ranges
                "typical_content_units_range": "15–25 content units",
                "page_types": ["category hubs", "comparisons", "case studies", "proof library", "deep FAQs"],
                "llm_capability_unlocked": "Recommend → cite (high confidence)",
                "what_ai_can_do_at_this_level": "AI proactively recommends you, cites your proof, and answers nuanced questions confidently.",
                "who_this_level_is_for": "Brands that compete on trust, differentiation, and want AI-first visibility as a channel.",
                "expected_shift": "More frequent and confident recommendations with better attribution/citations.",
            },
            "current_assessment": "",
        }

    def _parse_int_range(self, text: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        if not text:
            return (None, None)
        # Supports '8-12', '8–12', '8 to 12', etc.
        nums = [int(n) for n in re.findall(r"\d+", text)]
        if not nums:
            return (None, None)
        if len(nums) == 1:
            return (nums[0], nums[0])
        return (min(nums[0], nums[1]), max(nums[0], nums[1]))

    def _estimate_current_coverage_level(self, audit_data: Dict[str, Any], pages_count: int) -> str:
        """
        UX guarantee directive:
        - <8 pages → Partial Baseline
        - 8–14 pages → Baseline
        - 15–24 pages → Recommended
        - 25+ pages → Authority
        Deterministic; does not depend on LLM-provided text.
        """
        if pages_count < 8:
            return "partial baseline"
        if pages_count <= 14:
            return "baseline"
        if pages_count <= 24:
            return "recommended"
        return "authority"

    def _normalize_numeric_range(self, text: Optional[str], fallback: str) -> str:
        """
        Ensure a numeric range string like '5–7' (never blank, never 'N/A', never '—').
        """
        if not text:
            return fallback
        if isinstance(text, str):
            t = text.strip()
            if not t or t in {"—", "-", "N/A"} or "n/a" in t.lower():
                return fallback
            lo, hi = self._parse_int_range(t)
            if lo is None or hi is None:
                return fallback
            return f"{lo}–{hi}"
        return fallback

    def _default_content_summary(self) -> Dict[str, Any]:
        """
        Deterministic fallback so the Growth Plan page never renders empty.
        """
        return {
            "total_content_units": "4–6 LLM-focused content units",
            "breakdown_by_type": {},
            "estimated_coverage_level": "baseline",
        }

    def _derive_growth_plan_summary(
        self,
        audit_data: Dict[str, Any],
        action_plan_data: Optional[Dict[str, Any]],
        coverage_levels: Dict[str, Any],
        pages_count: int,
    ) -> Dict[str, Any]:
        ap = action_plan_data or {}
        content_summary = ap.get("content_summary") or {}

        current_level = self._estimate_current_coverage_level(audit_data, pages_count)
        after = content_summary.get("estimated_coverage_level") or "baseline"

        if after == "baseline":
            next_level = "recommended"
        elif after == "recommended":
            next_level = "authority"
        else:
            next_level = None

        plan_min, plan_max = self._parse_int_range(content_summary.get("total_content_units"))
        if next_level is None:
            needed = "0–0"
        else:
            next_min, next_max = self._parse_int_range(
                (coverage_levels.get(next_level) or {}).get("typical_content_units_range")
            )
            if plan_min is None or plan_max is None or next_min is None or next_max is None:
                needed = "5–7"
            else:
                delta_min = max(0, next_min - plan_max)
                delta_max = max(0, next_max - plan_min)
                if delta_min == 0 and delta_max == 0:
                    needed = "0–0"
                elif delta_min == delta_max:
                    needed = f"{delta_min}–{delta_max}"
                else:
                    needed = f"{delta_min}–{delta_max}"

        return {
            "current_coverage_level": current_level,
            "coverage_after_plan": after,
            "content_units_needed_for_next_level": needed,
        }
    
    def render_html(
        self, 
        audit_data: Dict[str, Any], 
        action_plan_data: Optional[Dict[str, Any]],
        domain: str
    ) -> str:
        """
        Render HTML from audit data (Stage A) and action plan (Stage B)
        """
        # Defensive hardening:
        # Stage B payloads can be absent (older audits) or partially missing keys in edge cases.
        # The template is tolerant, but we still normalize here so report generation never fails.
        pages_count = len(((audit_data or {}).get("appendix") or {}).get("sampled_urls") or [])

        if isinstance(action_plan_data, dict):
            required = {"recommended_pages", "coverage_levels", "content_summary", "impact_forecast", "measurement_plan"}
            missing = sorted([k for k in required if k not in action_plan_data])
            if missing:
                print(f"[REPORT] ⚠️ Stage B payload missing keys: {missing}. Continuing with partial Stage B rendering.")

        # Normalize decision-layer data so Coverage Levels are NEVER empty.
        default_cov = self._default_coverage_levels()
        cov_in = (action_plan_data or {}).get("coverage_levels") if isinstance(action_plan_data, dict) else None
        if not isinstance(cov_in, dict):
            coverage_levels = deepcopy(default_cov)
        else:
            coverage_levels = deepcopy(cov_in)
            for lvl in ["baseline", "recommended", "authority"]:
                if not isinstance(coverage_levels.get(lvl), dict):
                    coverage_levels[lvl] = deepcopy(default_cov[lvl])
                else:
                    for k, v in default_cov[lvl].items():
                        coverage_levels[lvl].setdefault(k, v)
                # Enforce fixed content unit ranges (never empty)
                coverage_levels[lvl]["typical_content_units_range"] = default_cov[lvl]["typical_content_units_range"]
            coverage_levels.setdefault("current_assessment", "")

        if not (coverage_levels.get("current_assessment") or "").strip():
            est = self._estimate_current_coverage_level(audit_data, pages_count)
            scores = (audit_data or {}).get("scores") or {}
            coverage_levels["current_assessment"] = (
                f"Estimated current coverage: {est}. "
                f"Based on {pages_count} analyzed pages and current AI recommendability {scores.get('recommendability', 'N/A')}/100."
            )

        # Growth plan decision summary (prefer Stage B, else derive).
        gp_in = (action_plan_data or {}).get("growth_plan_summary") if isinstance(action_plan_data, dict) else None
        if isinstance(gp_in, dict) and {"current_coverage_level", "coverage_after_plan", "content_units_needed_for_next_level"} <= set(gp_in.keys()):
            growth_plan_summary = deepcopy(gp_in)
        else:
            growth_plan_summary = self._derive_growth_plan_summary(audit_data, action_plan_data, coverage_levels, pages_count)

        # Ensure next-step value is ALWAYS a numeric range string
        growth_plan_summary["content_units_needed_for_next_level"] = self._normalize_numeric_range(
            growth_plan_summary.get("content_units_needed_for_next_level"),
            fallback="5–7",
        )

        # Normalize content summary so Growth Plan never has empty values
        content_summary_in = (action_plan_data or {}).get("content_summary") if isinstance(action_plan_data, dict) else None
        if isinstance(content_summary_in, dict) and {"total_content_units", "breakdown_by_type", "estimated_coverage_level"} <= set(content_summary_in.keys()):
            content_summary = deepcopy(content_summary_in)
        else:
            content_summary = self._default_content_summary()
        # Ensure total_content_units is not blank/dash and is always meaningful
        if not str(content_summary.get("total_content_units") or "").strip() or str(content_summary.get("total_content_units")).strip() == "—":
            content_summary["total_content_units"] = self._default_content_summary()["total_content_units"]

        # Pass a normalized Stage B object (backward compatible), plus always-present decision variables.
        normalized_action_plan = deepcopy(action_plan_data) if isinstance(action_plan_data, dict) else action_plan_data
        if isinstance(normalized_action_plan, dict):
            normalized_action_plan.setdefault("coverage_levels", coverage_levels)
            normalized_action_plan.setdefault("growth_plan_summary", growth_plan_summary)
            normalized_action_plan.setdefault("content_summary", content_summary)

        template = self.jinja_env.get_template("audit_report.html")
        
        html = template.render(
            audit=audit_data,
            action_plan=normalized_action_plan,  # Stage B data (can be None for backward compat)
            coverage_levels=coverage_levels,     # Always present (decision section must never be empty)
            growth_plan_summary=growth_plan_summary,  # Always present (used when Stage B is partial/older)
            domain=domain,
            date=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )
        
        return html
    
    def generate_pdf(self, html_content: str, output_path: str):
        """Generate PDF from HTML"""
        # Lazy import so PDF dependencies cannot break URL-first product runtime.
        # PDF export is optional and MUST NOT block audits.
        from weasyprint import HTML  # type: ignore
        HTML(string=html_content).write_pdf(output_path)

    def build_report_view_model(
        self,
        *,
        job_id: str,
        domain: str,
        locale: Optional[str],
        generated_at: Optional[str],
        model: Optional[str],
        audit_data: Dict[str, Any],
        action_plan_data: Optional[Dict[str, Any]],
        sampled_urls: Optional[list[str]],
    ) -> Dict[str, Any]:
        """
        Build a normalized, URL-first report payload.

        Hard guarantees:
        - fixed keys exist
        - never returns empty/blank values for decision-critical fields
        - includes limited-data/estimated flags for UI tooltips
        """
        pages_count = len(((audit_data or {}).get("appendix") or {}).get("sampled_urls") or [])
        limited_data = pages_count < 8
        stage_b_missing = not isinstance(action_plan_data, dict)

        # Normalize decision-layer data so Coverage Levels are NEVER empty.
        default_cov = self._default_coverage_levels()
        cov_in = (action_plan_data or {}).get("coverage_levels") if isinstance(action_plan_data, dict) else None
        if not isinstance(cov_in, dict):
            coverage_levels = deepcopy(default_cov)
        else:
            coverage_levels = deepcopy(cov_in)
            for lvl in ["baseline", "recommended", "authority"]:
                if not isinstance(coverage_levels.get(lvl), dict):
                    coverage_levels[lvl] = deepcopy(default_cov[lvl])
                else:
                    for k, v in default_cov[lvl].items():
                        coverage_levels[lvl].setdefault(k, v)
                # Enforce fixed content unit ranges (never empty)
                coverage_levels[lvl]["typical_content_units_range"] = default_cov[lvl]["typical_content_units_range"]
            coverage_levels.setdefault("current_assessment", "")

        if not (coverage_levels.get("current_assessment") or "").strip():
            est = self._estimate_current_coverage_level(audit_data, pages_count)
            scores = (audit_data or {}).get("scores") or {}
            coverage_levels["current_assessment"] = (
                f"Estimated current coverage: {est}. "
                f"Based on {pages_count} analyzed pages and current AI recommendability {scores.get('recommendability', 'N/A')}/100."
            )

        # Growth plan decision summary (prefer Stage B, else derive).
        gp_in = (action_plan_data or {}).get("growth_plan_summary") if isinstance(action_plan_data, dict) else None
        if (
            isinstance(gp_in, dict)
            and {"current_coverage_level", "coverage_after_plan", "content_units_needed_for_next_level"} <= set(gp_in.keys())
        ):
            growth_plan_summary = deepcopy(gp_in)
        else:
            growth_plan_summary = self._derive_growth_plan_summary(audit_data, action_plan_data, coverage_levels, pages_count)

        # Ensure next-step value is ALWAYS a numeric range string
        growth_plan_summary["content_units_needed_for_next_level"] = self._normalize_numeric_range(
            growth_plan_summary.get("content_units_needed_for_next_level"),
            fallback="5–7",
        )

        # Normalize content summary so Growth Plan never has empty values
        content_summary_in = (action_plan_data or {}).get("content_summary") if isinstance(action_plan_data, dict) else None
        if (
            isinstance(content_summary_in, dict)
            and {"total_content_units", "breakdown_by_type", "estimated_coverage_level"} <= set(content_summary_in.keys())
        ):
            content_summary = deepcopy(content_summary_in)
        else:
            content_summary = self._default_content_summary()
        if not str(content_summary.get("total_content_units") or "").strip() or str(content_summary.get("total_content_units")).strip() == "—":
            content_summary["total_content_units"] = self._default_content_summary()["total_content_units"]

        # Determine current bucket for UI highlights
        current_raw = str(growth_plan_summary.get("current_coverage_level") or "partial baseline").lower()
        if "authority" in current_raw:
            current_bucket = "authority"
        elif "recommended" in current_raw:
            current_bucket = "recommended"
        else:
            current_bucket = "baseline"
        is_partial = "partial" in current_raw

        return {
            "meta": {
                "job_id": job_id,
                "domain": domain,
                "locale": locale,
                "generated_at": generated_at,
                "model": model,
                "pipeline_version": "3.0-url-first",
                "pages_analyzed": pages_count,
                "limited_data": limited_data,
                "estimated": limited_data or stage_b_missing,
            },
            "raw": {
                "core_audit": audit_data,
                "action_plan": action_plan_data,
                "sampled_urls": sampled_urls or [],
            },
            "normalized": {
                "coverage_levels": coverage_levels,
                "growth_plan_summary": growth_plan_summary,
                "content_summary": content_summary,
                "current_bucket": current_bucket,
                "is_partial": is_partial,
            },
        }
    
    async def generate_report(
        self, 
        job_id: str, 
        audit_json: Dict[str, Any],
        action_plan_json: Optional[Dict[str, Any]],
        sampled_urls: list[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Generate HTML and PDF reports, save to DB (audit_outputs table)
        
        Args:
            job_id: Audit job ID
            audit_json: Stage A output (core audit with scores, gaps, quick wins)
            action_plan_json: Stage B output (recommended pages, impact forecast)
            sampled_urls: List of URLs that were analyzed
            
        Returns:
            tuple: (html_path, pdf_path)
        """
        
        # Get job
        result = await self.db.execute(
            select(AuditJob).where(AuditJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        html_content: Optional[str] = None
        html_path: Optional[str] = None

        if settings.enable_html_export:
            # Update status
            job.status = "generating_report"
            job.current_stage = "rendering_html"
            job.progress_percent = 85
            await self.db.commit()
            await asyncio.sleep(1.0)  # Give frontend time to display this stage

            print("[REPORT] Rendering HTML (optional legacy export)...")

            # Render HTML with both Stage A and Stage B data
            html_content = self.render_html(audit_json, action_plan_json, job.target_domain)

            # Save HTML to disk
            os.makedirs(settings.reports_dir, exist_ok=True)
            html_filename = f"audit_{job_id}.html"
            html_path = os.path.join(settings.reports_dir, html_filename)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"[REPORT] HTML saved: {html_path}")
        
        pdf_path: Optional[str] = None
        if settings.enable_pdf_export and html_content:
            # Generate PDF (optional export)
            job.current_stage = "generating_pdf"
            job.progress_percent = 90
            await self.db.commit()
            await asyncio.sleep(0.5)  # Give frontend time to display this stage

            print("[REPORT] Generating PDF (optional export)...")

            pdf_filename = f"audit_{job_id}.pdf"
            pdf_path = os.path.join(settings.reports_dir, pdf_filename)

            try:
                self.generate_pdf(html_content, pdf_path)
                print(f"[REPORT] PDF saved: {pdf_path}")
            except Exception as e:
                # Never block audits due to PDF failure
                print(f"[REPORT] ⚠️ PDF export failed (continuing without PDF): {e}")
                pdf_path = None
        
        # Save to audit_outputs table (single source of truth)
        job.current_stage = "saving_to_database"
        job.progress_percent = 95
        await self.db.commit()
        await asyncio.sleep(0.5)  # Give frontend time to display this stage
        
        # Check if output already exists (retry scenario)
        existing = await self.db.execute(
            select(AuditOutput).where(AuditOutput.audit_job_id == job_id)
        )
        output = existing.scalar_one_or_none()
        
        if output:
            # Archive previous version for retention UI ("change since last run")
            try:
                snap = AuditOutputSnapshot(
                    audit_job_id=job.id,
                    audit_json=output.audit_json,
                    action_plan_json=output.action_plan_json,
                    sampled_urls=output.sampled_urls,
                    model=output.model,
                    created_at=output.created_at,
                    run_id=output.run_id,
                )
                self.db.add(snap)
                print("[REPORT] Archived previous output into audit_output_snapshots")
            except Exception as e:
                # Never block audits due to snapshot archival
                print(f"[REPORT] ⚠️ Snapshot archival failed (continuing): {e}")

            # Update existing
            output.audit_json = audit_json
            output.action_plan_json = action_plan_json  # Stage B data
            output.report_html = html_content
            output.pdf_path = pdf_path
            output.model = settings.openai_model
            output.sampled_urls = sampled_urls
            output.run_id = uuid.uuid4()  # New run ID
            output.created_at = datetime.utcnow()  # Treat as "last updated" for dashboard
            print("[REPORT] Updated existing audit_output record")
        else:
            # Create new
            output = AuditOutput(
                audit_job_id=job.id,
                audit_json=audit_json,
                action_plan_json=action_plan_json,  # Stage B data
                report_html=html_content,
                pdf_path=pdf_path,
                model=settings.openai_model,
                sampled_urls=sampled_urls,
                run_id=uuid.uuid4()
            )
            self.db.add(output)
            print("[REPORT] Created new audit_output record")
        
        # Update job (keep legacy fields for backward compatibility)
        job.report_html_path = html_path
        job.report_pdf_path = pdf_path
        job.report_generated_at = datetime.utcnow()
        job.status = "completed"
        job.progress_percent = 100
        await self.db.commit()
        
        print("[REPORT] Report generation complete!")
        print(f"[REPORT] Stage A: Core audit saved")
        if action_plan_json:
            print(f"[REPORT] Stage B: Action plan with {len(action_plan_json.get('recommended_pages', []))} recommended pages")
        
        return (html_path, pdf_path)
