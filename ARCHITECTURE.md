# LLM Audit Engine - Architecture Documentation

## System Overview

The LLM Audit Engine is a job-based pipeline that analyzes websites for "LLM-friendliness" - how well AI models like ChatGPT and Perplexity would recommend them.

```
User Input → API → Database (pending job) 
            ↓
         Worker picks up job
            ↓
    [Scraping Stage] → Store pages in DB
            ↓
    [LLM Analysis] → Generate structured audit JSON
            ↓
    [Report Generation] → HTML + PDF
            ↓
         User downloads PDF/JSON
```

## Technology Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - ORM with async support
- **PostgreSQL** - Primary database (JSONB for audit results)
- **httpx** - Async HTTP client for scraping
- **BeautifulSoup4** - HTML parsing
- **OpenAI SDK** - GPT-4o API integration
- **Jinja2** - HTML templating
- **WeasyPrint** - HTML to PDF conversion

### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first CSS
- **TanStack Query** - Data fetching and polling

## Database Schema

### Table: `audit_jobs`

Main job tracking and results storage.

```sql
audit_jobs (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- Input
    target_domain VARCHAR(255),
    competitor_domains JSONB,          -- ["domain1.com", ...]
    locale VARCHAR(10),
    company_description TEXT,
    products_services TEXT,
    
    -- Status tracking
    status VARCHAR(50),                 -- pending/scraping/llm_processing/generating_report/completed/failed
    current_stage VARCHAR(50),
    progress_percent INTEGER,
    error_message TEXT,
    
    -- Outputs
    audit_result JSONB,                -- Full structured audit from LLM
    report_pdf_path VARCHAR(500),
    report_html_path VARCHAR(500),
    
    -- Timing metadata
    scraping_started_at TIMESTAMP,
    scraping_completed_at TIMESTAMP,
    llm_started_at TIMESTAMP,
    llm_completed_at TIMESTAMP,
    report_generated_at TIMESTAMP,
    total_pages_scraped INTEGER
)
```

### Table: `scraped_pages`

Stores all scraped web pages for analysis.

```sql
scraped_pages (
    id UUID PRIMARY KEY,
    audit_job_id UUID REFERENCES audit_jobs(id) ON DELETE CASCADE,
    
    url TEXT,
    domain VARCHAR(255),
    is_target BOOLEAN,                 -- true = target, false = competitor
    
    html_content TEXT,
    text_content TEXT,
    title VARCHAR(500),
    meta_description TEXT,
    
    scraped_at TIMESTAMP,
    status_code INTEGER,
    content_type VARCHAR(100),
    word_count INTEGER,
    
    url_hash VARCHAR(64) UNIQUE        -- SHA256 for deduplication
)
```

## Core Components

### 1. API Layer (`app/main.py`, `app/api/routes.py`)

**Endpoints:**
- `POST /api/audit` - Create new audit job
- `GET /api/audit/:id` - Get job status
- `GET /api/audit/:id/pdf` - Download PDF
- `GET /api/audit/:id/json` - Download JSON
- `GET /api/audit/:id/html` - Preview HTML

**Responsibilities:**
- Accept user input
- Create job records
- Serve files
- CORS handling

### 2. Web Scraper (`app/services/scraper.py`)

**Key Features:**
- **SSRF Protection**: Blocks localhost, private IPs, non-HTTP(S) protocols
- **Sitemap Discovery**: Tries to find and parse sitemap.xml
- **URL Deduplication**: SHA256 hash of normalized URLs
- **Rate Limiting**: 200ms delay between requests
- **Size Limits**: Max 5MB per page
- **Timeouts**: 10s per request, 5min total

**Flow:**
1. Start with homepage or sitemap
2. Extract links from navigation
3. Scrape up to 60 pages (target) or 15 (competitor)
4. Store HTML + extracted text in DB
5. Track progress in job record

### 3. LLM Auditor (`app/services/llm_auditor.py`)

**Key Features:**
- Selects 10-15 representative pages (highest word count)
- Builds comprehensive prompt with context
- Uses GPT-4o with `response_format: json_object`
- Validates output with Pydantic schemas

**Prompt Strategy:**
- System: "You are an expert LLM traffic auditor..."
- User: Context about company + sampled pages + competitor data
- Output: Structured JSON with scores, gaps, recommendations

**JSON Schema Enforcement:**
- Hard limits on array sizes (prevents bloat)
- Required fields validation
- Enum types for priority/effort levels

### 4. Report Generator (`app/services/report_generator.py`)

**Key Features:**
- Jinja2 templates for HTML rendering
- WeasyPrint for PDF generation
- Color-coded scores and priorities
- Responsive 5-page layout

**Report Structure:**
1. Executive Summary (scores + LLM simulation)
2. Top Gaps Analysis (table)
3. Action Plan (quick wins + timeline)
4. Competitive Angles (if competitors provided)
5. Appendix (stats + sampled URLs)

### 5. Worker Process (`app/worker.py`)

**Architecture:**
- Simple async loop (no Celery/Redis complexity)
- Polls DB every 5s for pending jobs
- Runs pipeline: scrape → LLM → report
- Updates job status at each stage
- Error handling with job.error_message

**Deployment:**
- Run as separate process: `python -m app.worker`
- Can run multiple workers (DB handles concurrency)
- Graceful shutdown on KeyboardInterrupt

## Data Flow

### Job Lifecycle

```
1. User submits form
   ↓
2. POST /api/audit creates job (status: pending)
   ↓
3. Worker picks up job
   ↓
4. Scraping stage (status: scraping)
   - Updates progress: 10% → 60%
   - Stores pages in scraped_pages table
   ↓
5. LLM stage (status: llm_processing)
   - Updates progress: 65% → 80%
   - Stores audit_result JSONB
   ↓
6. Report stage (status: generating_report)
   - Updates progress: 85% → 100%
   - Saves HTML and PDF files
   ↓
7. Complete (status: completed)
   - User downloads files
```

### Error Handling

If any stage fails:
- Job status → `failed`
- Error message stored in `job.error_message`
- No retry logic (MVP - user creates new job)

## Security Considerations

### SSRF Protection
- Whitelist: Only `http://` and `https://`
- Blacklist: localhost, 127.0.0.1, private IP ranges
- Hostname validation before DNS resolution

### Input Validation
- Pydantic schemas for all API inputs
- Max 5 competitors
- Domain format validation

### Rate Limiting
- 200ms delay between scraping requests
- Max 60 pages per domain
- Total timeout: 5 minutes

### File Storage
- Reports stored in configurable directory
- UUID-based filenames (no user input in paths)
- Served via FastAPI StaticFiles

## Performance Characteristics

### Timing Estimates
- **Scraping**: 2-5 minutes (depends on site speed)
- **LLM Analysis**: 1-2 minutes (GPT-4o API call)
- **Report Generation**: 10-30 seconds (PDF rendering)
- **Total**: ~5-10 minutes per audit

### Resource Usage
- **Database**: ~1-10 MB per job (depends on scraped content)
- **Disk**: ~500KB per PDF report
- **Memory**: ~200-500 MB per worker process
- **API Calls**: 1 GPT-4o call per audit (~$0.10-0.30)

## Scalability Considerations

### Current MVP Limitations
- Single-threaded scraping per job
- No job queue (simple DB polling)
- No distributed workers
- No caching

### Future Scaling Path
1. Add Redis for job queue (Celery/RQ)
2. Horizontal worker scaling
3. CDN for report files
4. Scraping parallelization
5. Result caching (same domain audits)

## Development Workflow

### Local Development
```bash
# Terminal 1: API
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Worker
cd backend
source venv/bin/activate
python -m app.worker

# Terminal 3: Frontend
cd frontend
npm run dev
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding New Features

**New audit field:**
1. Update `app/schemas.py` (AuditResult)
2. Update `app/services/llm_auditor.py` (JSON schema)
3. Update `app/templates/audit_report.html` (rendering)

**New scraping source:**
1. Update `app/services/scraper.py`
2. Consider adding to `scraped_pages` metadata

## Monitoring & Debugging

### Key Log Points
- Worker: Stage transitions, page counts, errors
- API: Request logs (FastAPI default)
- Database: Query performance (SQLAlchemy echo)

### Health Checks
- `GET /health` - API server status
- Database connection via Alembic
- Worker: Check process is running

### Common Issues
1. **Worker not processing**: Check DB connection, job status
2. **Scraping timeout**: Reduce MAX_PAGES or increase timeout
3. **LLM errors**: Check API key, rate limits
4. **PDF generation fails**: Install system dependencies (Pango, etc.)

## Configuration

All configuration in `.env` file:

```bash
DATABASE_URL=postgresql+asyncpg://...
OPENAI_API_KEY=sk-...
MAX_PAGES_TARGET=60
MAX_PAGES_COMPETITOR=15
REQUEST_TIMEOUT=10
REPORTS_DIR=./reports
```

Changes require service restart.

## Testing Strategy

### Manual Testing
1. Run audit on known website (stripe.com, etc.)
2. Verify all stages complete
3. Check PDF quality
4. Validate JSON structure

### Automated Testing (Future)
- Unit tests for scraper (mocked HTTP)
- LLM tests with fixture responses
- E2E tests with test database

## Deployment Architecture

### Recommended Production Setup

```
┌─────────────┐
│   Nginx     │ (SSL, static files)
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │ (Gunicorn + Uvicorn workers)
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────────┐
│  PostgreSQL │◄────┤ Worker(s)    │
└─────────────┘     └──────────────┘
       │
┌──────▼──────┐
│ /reports/   │ (Persistent volume)
└─────────────┘
```

### Environment Variables (Production)
- Use secrets manager (AWS Secrets, etc.)
- Separate DB credentials
- Read-only API user for workers

### Scaling Workers
```bash
# Run multiple workers
python -m app.worker &
python -m app.worker &
python -m app.worker &
```

Workers coordinate via DB locks (implicit in "get pending job" query).


