# Quick Start Guide

Get the LLM Audit Engine running in **ONE COMMAND**.

## Prerequisites

- **Docker** ([Install Docker Desktop](https://www.docker.com/products/docker-desktop/))
- **Python 3.10+**
- **Node.js 18+**
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))

## Step 1: Configure (30 seconds)

```bash
# Copy environment template
cp env.example backend/.env

# Edit and add your OpenAI API key
nano backend/.env  # or use any editor
```

**Important:** Replace `sk-CHANGE-THIS-TO-YOUR-REAL-KEY` with your actual OpenAI API key.

## Step 2: Run (ONE command!)

```bash
make dev
```

Or directly:

```bash
./dev.sh
```

That's it! 🎉

The script will:
- ✅ Start PostgreSQL (Docker)
- ✅ Create database
- ✅ Run migrations
- ✅ Install all dependencies
- ✅ Start API server
- ✅ Start worker
- ✅ Start frontend

## Step 3: Open Browser

Go to: **http://localhost:3000**

---

## Other Commands

```bash
make stop   # Stop all services
make logs   # View logs
make clean  # Clean everything and start fresh
```

## Troubleshooting

**"Docker not found"**
- Install Docker Desktop

**"OPENAI_API_KEY not configured"**
- Edit `backend/.env` and set your real API key

**Port already in use**
```bash
make stop  # Kill any running processes
make dev   # Try again
```

**View logs**
```bash
tail -f logs/api.log      # API server
tail -f logs/worker.log   # Background worker
tail -f logs/frontend.log # Frontend dev server
```

## Test Audit

Use these values for your first test:

**Target Domain:** `stripe.com`

**Competitors:** `square.com`, `paypal.com`

**Locale:** `en-US`

**Description:**
```
Stripe provides payment processing APIs and financial infrastructure 
for businesses of all sizes to accept online payments.
```

**Products/Services:**
```
Payment APIs, subscription billing, fraud prevention, 
financial services platform
```

Click "Run Audit" and wait ~5-8 minutes.

## What to Expect

1. **Scraping (2-5 min)**: Downloads ~60 pages from target, ~15 per competitor
2. **LLM Analysis (1-2 min)**: GPT-4o analyzes and generates structured audit
3. **Report Generation (10-30 sec)**: Creates HTML and PDF

When complete, download the PDF report!

## Troubleshooting

**"Database connection failed"**
- Check PostgreSQL is running: `psql llm_audit`

**"OpenAI authentication error"**
- Verify your API key in `backend/.env`

**"Module not found"**
- Run `pip install -r requirements.txt` again

**"Port already in use"**
- Kill process: `lsof -ti:8000 | xargs kill -9`

## Full Documentation

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Complete setup instructions
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture
- [README.md](README.md) - Project overview

## Next Steps

Once working:
1. Try your own website
2. Customize the HTML template
3. Adjust scraping limits in `.env`
4. Review the JSON output structure

