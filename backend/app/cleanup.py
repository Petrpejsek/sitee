"""Cleanup script for old audit reports and files"""
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models import AuditOutput, AuditJob
from app.config import get_settings

settings = get_settings()


async def cleanup_old_reports():
    """Clean up reports older than retention period"""
    
    print("="*60)
    print("LLM Audit Engine - Report Cleanup")
    print("="*60)
    print(f"Retention period: {settings.reports_retention_days} days")
    print(f"Reports directory: {settings.reports_dir}\n")
    
    cutoff_date = datetime.utcnow() - timedelta(days=settings.reports_retention_days)
    
    async with AsyncSessionLocal() as db:
        # Find old outputs
        result = await db.execute(
            select(AuditOutput, AuditJob)
            .join(AuditJob, AuditOutput.audit_job_id == AuditJob.id)
            .where(AuditOutput.created_at < cutoff_date)
        )
        
        old_outputs = result.all()
        
        if not old_outputs:
            print("✓ No old reports to clean up")
            return
        
        print(f"Found {len(old_outputs)} reports older than {cutoff_date.strftime('%Y-%m-%d')}")
        print()
        
        deleted_files = 0
        deleted_records = 0
        errors = 0
        
        for output, job in old_outputs:
            try:
                # Delete PDF file if exists
                if output.pdf_path and os.path.exists(output.pdf_path):
                    os.remove(output.pdf_path)
                    print(f"✓ Deleted PDF: {output.pdf_path}")
                    deleted_files += 1
                
                # Delete HTML file if exists (legacy)
                if job.report_html_path and os.path.exists(job.report_html_path):
                    os.remove(job.report_html_path)
                    print(f"✓ Deleted HTML: {job.report_html_path}")
                    deleted_files += 1
                
                # Delete database record
                await db.delete(output)
                deleted_records += 1
                
            except Exception as e:
                print(f"✗ Error cleaning up audit {output.audit_job_id}: {e}")
                errors += 1
        
        await db.commit()
        
        print()
        print("="*60)
        print(f"Cleanup complete:")
        print(f"  Files deleted: {deleted_files}")
        print(f"  DB records deleted: {deleted_records}")
        print(f"  Errors: {errors}")
        print("="*60)


async def cleanup_orphaned_files():
    """Clean up PDF files without DB reference"""
    
    print("\nChecking for orphaned files...")
    
    reports_path = Path(settings.reports_dir)
    if not reports_path.exists():
        print("Reports directory doesn't exist")
        return
    
    async with AsyncSessionLocal() as db:
        # Get all PDF paths from DB
        result = await db.execute(select(AuditOutput.pdf_path))
        db_paths = set(row[0] for row in result.all() if row[0])
        
        # Check files in directory
        orphaned = []
        for pdf_file in reports_path.glob("audit_*.pdf"):
            if str(pdf_file) not in db_paths:
                orphaned.append(pdf_file)
        
        if not orphaned:
            print("✓ No orphaned files found")
            return
        
        print(f"Found {len(orphaned)} orphaned files:")
        for file in orphaned:
            try:
                os.remove(file)
                print(f"✓ Deleted orphaned: {file.name}")
            except Exception as e:
                print(f"✗ Error deleting {file.name}: {e}")


async def main():
    """Main cleanup function"""
    await cleanup_old_reports()
    await cleanup_orphaned_files()


if __name__ == "__main__":
    asyncio.run(main())


