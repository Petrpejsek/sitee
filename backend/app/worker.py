"""
Background worker for processing audit jobs
NEW: AI Visibility Sales Report (Stages A-E in single LLM call)
- Stage A: AI Visibility Status (ChatGPT, Gemini, Perplexity %)
- Stage B: Why AI Does Not Recommend (blockers)
- Stage C: What AI Needs (content types)
- Stage D: Package Tiers (Starter, Growth, Authority)
- Stage E: Business Impact & Recommendation (close)

IMPORTANT: Uses PID file locking to ensure only ONE worker runs at a time!
"""
import asyncio
import sys
import os
import signal
import atexit
from pathlib import Path
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, init_db
from app.models import AuditJob
from app.services.scraper import WebScraper
from app.services.llm_auditor import LLMAuditor
from app.services.report_generator import ReportGenerator

# PID file for single-instance enforcement
PID_FILE = Path(__file__).parent.parent.parent / "logs" / "worker.pid"


class SingleInstanceLock:
    """Ensure only one worker instance runs at a time"""
    
    def __init__(self, pid_file: Path):
        self.pid_file = pid_file
        self.locked = False
    
    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if successful."""
        # Create logs directory if needed
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if another worker is running
        if self.pid_file.exists():
            try:
                old_pid = int(self.pid_file.read_text().strip())
                # Check if process is still running
                try:
                    os.kill(old_pid, 0)  # Signal 0 = check if exists
                    print(f"❌ Another worker is already running (PID: {old_pid})")
                    print(f"   Kill it first: kill {old_pid}")
                    print(f"   Or use: ./dev.sh worker restart")
                    return False
                except ProcessLookupError:
                    # Process doesn't exist, stale PID file
                    print(f"⚠️  Removing stale PID file (old PID: {old_pid})")
                except PermissionError:
                    # Process exists but we can't signal it
                    print(f"❌ Another worker is running (PID: {old_pid}, permission denied)")
                    return False
            except (ValueError, FileNotFoundError):
                pass  # Invalid PID file, will overwrite
        
        # Write our PID
        self.pid_file.write_text(str(os.getpid()))
        self.locked = True
        
        # Register cleanup
        atexit.register(self.release)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        return True
    
    def release(self):
        """Release the lock"""
        if self.locked and self.pid_file.exists():
            try:
                # Only remove if it's our PID
                current_pid = int(self.pid_file.read_text().strip())
                if current_pid == os.getpid():
                    self.pid_file.unlink()
                    self.locked = False
            except (ValueError, FileNotFoundError, PermissionError):
                pass
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\n⚡ Received signal {signum}, shutting down...")
        self.release()
        sys.exit(0)


async def get_pending_job(db: AsyncSession) -> AuditJob | None:
    """Get next pending job"""
    result = await db.execute(
        select(AuditJob)
        .where(AuditJob.status == "pending")
        .order_by(AuditJob.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def run_audit_pipeline(job: AuditJob, db: AsyncSession):
    """
    Run complete audit pipeline for a job with HARD GUARDS
    
    Pipeline stages:
    1. Scraping
    2. Stage A: Core LLM Audit (scoring + gaps + quick wins)
    3. Stage B: Action Plan Builder (pages + outlines + impact forecast)
    4. Report Generation (combines both stages)
    """
    job_id = str(job.id)
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting audit pipeline for job {job_id}")
    print(f"   Domain: {job.target_domain}")
    print(f"   Competitors: {', '.join(job.competitor_domains) if job.competitor_domains else 'None'}")
    print(f"{'='*60}\n")
    
    scraper = None
    priority_urls = []
    audit_result = None
    action_plan_result = None
    sampled_urls = []
    
    try:
        # =====================================================================
        # Stage 1: Scraping
        # =====================================================================
        print(f"[STAGE 1/4] 🌐 SCRAPING")
        try:
            scraper = WebScraper(db)
            total_pages, priority_urls, scrape_debug = await scraper.scrape_job(job_id)
            print(f"[STAGE 1/4] ✅ SCRAPING COMPLETE - {total_pages} pages scraped\n")
        except Exception as e:
            raise ValueError(f"Scraping failed: {str(e)}")
        
        # =====================================================================
        # LIMITED-DATA MODE: 0 pages scraped should NOT kill the sales engine
        # =====================================================================
        if total_pages == 0:
            debug_info = scrape_debug.to_dict() if scrape_debug else {}
            blocked_reason = debug_info.get("blocked_reason", "unknown")
            homepage_error = debug_info.get("homepage_fetch_error", "")

            print(f"\n{'='*60}")
            print("⚠️  LIMITED-DATA MODE: 0 pages scraped (continuing to sales report anyway)")
            print(f"   Blocked reason: {blocked_reason}")
            if homepage_error:
                print(f"   Homepage error: {homepage_error}")
            print(f"{'='*60}\n")

            # Keep job moving; surface a non-fatal note for the UI.
            job.error_message = (
                f"SCRAPE_LIMITED_DATA: 0 pages fetched (blocked: {blocked_reason}). "
                f"Continuing with limited data using business inputs. "
                f"See scrape_debug for details."
            )
            job.updated_at = datetime.utcnow()
            await db.commit()
        
        # =====================================================================
        # Stage 2 & 3: LLM Analysis (AI Visibility Sales Report)
        # =====================================================================
        print(f"[STAGE 2-3/4] 🧠 AI VISIBILITY SALES REPORT")
        
        try:
            auditor = LLMAuditor(db)
            # run_audit now returns 3 values: (sales_report, backward_compat_action_plan, sampled_urls)
            audit_result, action_plan_result, sampled_urls = await auditor.run_audit(job_id, priority_urls)
            
            print(f"[STAGE 2-3/4] ✅ AI VISIBILITY SALES REPORT COMPLETE")
            # Support both older (stage_a_visibility...) and new (stage_1_ai_visibility...) schemas.
            vis = audit_result.get("stage_1_ai_visibility") or audit_result.get("stage_a_visibility") or {}
            reasons = audit_result.get("stage_2_why_ai_chooses_others") or audit_result.get("stage_b_blockers") or []
            impact = audit_result.get("stage_5_business_impact") or audit_result.get("stage_e_recommendation") or {}
            print(f"   ChatGPT visibility: {vis.get('chatgpt_visibility_percent', 'N/A')}% ({vis.get('chatgpt_label', 'N/A')})")
            print(f"   Reasons: {len(reasons) if isinstance(reasons, list) else 'N/A'}")
            print(f"   Recommended: {impact.get('recommended_option', impact.get('recommended_package', 'N/A'))}")
            print(f"   Sampled: {len(sampled_urls)} URLs\n")
            
        except ValueError as e:
            raise ValueError(f"LLM analysis failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"LLM processing error: {str(e)}")
        
        # =====================================================================
        # Stage 4: Report Generation (combines both stages)
        # =====================================================================
        print(f"[STAGE 4/4] 📄 REPORT GENERATION")
        try:
            generator = ReportGenerator(db)
            html_path, pdf_path = await generator.generate_report(
                job_id, 
                audit_result, 
                action_plan_result,  # New: pass Stage B result
                sampled_urls
            )
            print(f"[STAGE 4/4] ✅ REPORT GENERATION COMPLETE")
            if html_path:
                print(f"   HTML: {html_path}")
            if pdf_path:
                print(f"   PDF: {pdf_path}")
            print("")
        except Exception as e:
            raise ValueError(f"Report generation failed: {str(e)}")
        
        print(f"{'='*60}")
        print(f"✅ Audit pipeline completed successfully for {job.target_domain}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ Audit pipeline failed for job {job_id}")
        print(f"   Error: {str(e)}")
        print(f"   Stage: {job.current_stage or 'unknown'}")
        print(f"{'='*60}\n")
        
        job.status = "failed"
        job.error_message = f"[{job.current_stage or 'unknown'}] {str(e)}"
        job.updated_at = datetime.utcnow()
        await db.commit()
        
        import traceback
        traceback.print_exc()
        
    finally:
        if scraper:
            try:
                await scraper.close()
            except Exception:
                pass


async def process_jobs():
    """Main worker loop - continuously process pending jobs"""
    print("="*60)
    print("👷 LLM Audit Engine Worker Started")
    print("   2-Stage Pipeline: Core Audit + Action Plan Builder")
    print(f"   PID: {os.getpid()}")
    print("="*60)
    print("⏳ Waiting for jobs...\n")
    
    while True:
        try:
            async with AsyncSessionLocal() as db:
                job = await get_pending_job(db)
                
                if job:
                    await run_audit_pipeline(job, db)
                else:
                    await asyncio.sleep(5)
                    
        except KeyboardInterrupt:
            print("\n\n👋 Worker shutting down...")
            break
        except Exception as e:
            print(f"⚠️  Worker error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(10)


async def main():
    """Main entry point with single-instance enforcement"""
    # Acquire lock
    lock = SingleInstanceLock(PID_FILE)
    if not lock.acquire():
        sys.exit(1)
    
    try:
        await init_db()
        await process_jobs()
    finally:
        lock.release()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
