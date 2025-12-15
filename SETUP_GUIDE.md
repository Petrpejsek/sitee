# LLM Audit Engine - Setup Guide

Complete setup and testing guide for the LLM Audit Engine MVP.

## Prerequisites

1. **Python 3.10+** - [Download](https://www.python.org/downloads/)
2. **Node.js 18+** - [Download](https://nodejs.org/)
3. **PostgreSQL 14+** - [Download](https://www.postgresql.org/download/)
4. **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)

## Step 1: PostgreSQL Setup

### Option A: Local PostgreSQL

```bash
# macOS (with Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb llm_audit

# Test connection
psql llm_audit
```

### Option B: Docker PostgreSQL

```bash
docker run --name llm-audit-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=llm_audit \
  -p 5432:5432 \
  -d postgres:14

# Test connection
docker exec -it llm-audit-postgres psql -U postgres -d llm_audit
```

## Step 2: Backend Setup

```bash
cd backend

# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/llm_audit
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4o
MAX_PAGES_TARGET=60
MAX_PAGES_COMPETITOR=15
REPORTS_DIR=./reports
BACKEND_URL=http://localhost:8000
EOF

# Run database migrations
alembic upgrade head

# Create reports directory
mkdir -p reports
```

## Step 3: Start Backend Services

You need **TWO terminal windows** for the backend:

### Terminal 1: API Server

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Test it: http://localhost:8000/health

### Terminal 2: Worker Process

```bash
cd backend
source venv/bin/activate
python -m app.worker
```

You should see:
```
============================================================
LLM Audit Engine Worker Started
============================================================
Waiting for jobs...
```

## Step 4: Frontend Setup

### New Terminal 3: Frontend Dev Server

```bash
cd frontend

# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh

# Start dev server
npm run dev
```

You should see:
```
  VITE v5.0.11  ready in 500 ms

  ➜  Local:   http://localhost:3000/
```

Open http://localhost:3000 in your browser!

## Step 5: Run Your First Audit

### Test Input Example

Use this data for your first test:

**Target Domain:** `stripe.com`

**Competitor Domains:**
- `square.com`
- `paypal.com`

**Locale:** `en-US`

**Company Description:**
```
Stripe is a technology company that builds economic infrastructure for the internet. 
Businesses of every size use our software to accept payments and manage their businesses online.
```

**Products/Services:**
```
Payment processing APIs, subscription billing, fraud prevention, 
financial services infrastructure, developer tools
```

### Expected Flow

1. Fill out the form and click "Run Audit"
2. You'll be redirected to the status page
3. Watch the progress:
   - **Pending** (0%)
   - **Scraping** (10-60%) - Takes 2-5 minutes
   - **LLM Processing** (65-80%) - Takes 1-2 minutes
   - **Generating Report** (85-100%) - Takes 10-30 seconds
4. When complete, download the PDF and JSON

### What You Should See in Worker Logs

```
============================================================
Starting audit pipeline for job abc-123...
Domain: stripe.com
Competitors: square.com, paypal.com
============================================================

[STAGE 1/3] SCRAPING
[SCRAPE] Starting target domain: stripe.com
[SCRAPE] Target domain done: 58 pages
[SCRAPE] Starting competitor 1/2: square.com
[SCRAPE] Competitor square.com done: 12 pages
...
[STAGE 1/3] SCRAPING COMPLETE - 82 pages scraped

[STAGE 2/3] LLM ANALYSIS
[LLM] Selecting representative pages...
[LLM] Selected 15 target pages, 10 competitor pages
[LLM] Calling GPT-4o...
[LLM] Audit complete!
[STAGE 2/3] LLM ANALYSIS COMPLETE

[STAGE 3/3] REPORT GENERATION
[REPORT] Rendering HTML...
[REPORT] HTML saved: ./reports/audit_abc-123.html
[REPORT] Generating PDF...
[REPORT] PDF saved: ./reports/audit_abc-123.pdf
[STAGE 3/3] REPORT GENERATION COMPLETE

============================================================
✓ Audit pipeline completed successfully for stripe.com
============================================================
```

## Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Fix:** Make sure PostgreSQL is running and the DATABASE_URL in `.env` is correct.

### OpenAI API Error

```
openai.AuthenticationError: Incorrect API key provided
```

**Fix:** Check your OPENAI_API_KEY in `backend/.env`

### WeasyPrint PDF Error

```
OSError: cannot load library 'gobject-2.0-0'
```

**Fix (macOS):**
```bash
brew install pango gdk-pixbuf libffi
```

**Fix (Ubuntu/Debian):**
```bash
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangocairo-1.0-0
```

### Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Fix:** Kill the process using the port:
```bash
# Find process
lsof -ti:8000

# Kill it
kill -9 <PID>
```

## Testing the API Directly

You can also test the API with curl:

```bash
# Create audit
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "target_domain": "example.com",
    "competitor_domains": ["competitor.com"],
    "locale": "en-US",
    "company_description": "Test company",
    "products_services": "Test products"
  }'

# Get status (replace JOB_ID)
curl http://localhost:8000/api/audit/JOB_ID

# Download PDF (replace JOB_ID)
curl http://localhost:8000/api/audit/JOB_ID/pdf --output report.pdf
```

## Production Deployment

For production deployment:

1. **Environment Variables**: Use proper secrets management
2. **Database**: Use managed PostgreSQL (AWS RDS, DigitalOcean, etc.)
3. **Backend**: Deploy with Gunicorn or in Docker
4. **Worker**: Run as systemd service or in separate container
5. **Frontend**: Build and serve static files (`npm run build`)
6. **Storage**: Use persistent volume for `/reports/`

Example Docker Compose setup can be created if needed.

## Next Steps

Once the basic audit is working:

1. Test with your own websites
2. Adjust scraping limits in `.env` if needed
3. Customize the HTML template for your branding
4. Add more locale options
5. Tune the LLM prompt for better results

## Support

If you encounter issues:

1. Check the worker logs for detailed error messages
2. Verify all services are running
3. Test database connection
4. Validate OpenAI API key
5. Check system requirements (Python, Node.js versions)


