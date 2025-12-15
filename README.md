# LLM Audit Engine

Internal tool for LLM Traffic / GEO audit of websites.

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env
# Edit .env and add your OPENAI_API_KEY

# Initialize database (make sure Postgres is running)
alembic upgrade head

# Run API server
uvicorn app.main:app --reload --port 8000

# Run worker (in separate terminal)
python -m app.worker
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Postgres
- **Frontend**: React + Vite + TailwindCSS
- **Scraping**: httpx + BeautifulSoup4
- **LLM**: OpenAI GPT-4o
- **PDF**: WeasyPrint

## Workflow

1. User submits audit request via form
2. Backend creates job in Postgres (status: pending)
3. Worker picks up job and runs:
   - Scraping stage (50-60 pages from target, 10-15 per competitor)
   - LLM processing (GPT-4o analyzes and returns structured JSON)
   - Report generation (HTML → PDF)
4. User polls for status and downloads PDF/JSON when complete

## Database

Tables:
- `audit_jobs` - Main job tracking
- `scraped_pages` - Scraped content storage

## API Endpoints

- `POST /api/audit` - Create new audit
- `GET /api/audit/:id` - Get job status
- `GET /api/audit/:id/pdf` - Download PDF report
- `GET /api/audit/:id/json` - Download JSON audit
- `GET /api/audit/:id/html` - Preview HTML report


