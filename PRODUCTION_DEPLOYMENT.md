# LLM Audit Engine - Production Deployment Guide

Complete guide for deploying LLM Audit Engine to a production VPS.

## Prerequisites

- Ubuntu 22.04 LTS server
- Domain name pointed to server IP
- Root or sudo access
- At least 2GB RAM, 20GB disk

## 1. Server Setup

### Update system

```bash
sudo apt update && sudo apt upgrade -y
```

### Install dependencies

```bash
# Python
sudo apt install -y python3.10 python3.10-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Node.js (for building frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Nginx
sudo apt install -y nginx

# System dependencies for WeasyPrint
sudo apt install -y python3-cffi python3-brotli libpango-1.0-0 libpangocairo-1.0-0

# Certbot for SSL
sudo apt install -y certbot python3-certbot-nginx
```

## 2. PostgreSQL Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL console:
CREATE DATABASE llm_audit;
CREATE USER llm_audit_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE llm_audit TO llm_audit_user;
\q
```

## 3. Application Setup

### Create application user

```bash
sudo useradd -r -m -s /bin/bash www-data
sudo mkdir -p /var/www/llm-audit-engine
sudo chown www-data:www-data /var/www/llm-audit-engine
```

### Deploy application

```bash
# Upload your code to /var/www/llm-audit-engine
# Or clone from git:
cd /var/www/llm-audit-engine
sudo -u www-data git clone <your-repo> .

# Backend setup
cd /var/www/llm-audit-engine/backend
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/pip install gunicorn

# Create .env file
sudo -u www-data cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://llm_audit_user:your-secure-password@localhost:5432/llm_audit
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4o
MAX_PAGES_TARGET=60
MAX_PAGES_COMPETITOR=15
REPORTS_DIR=/var/www/llm-audit-engine/reports
REPORTS_RETENTION_DAYS=30
BACKEND_URL=https://your-domain.com
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
ENVIRONMENT=production
EOF

# Create reports directory
sudo mkdir -p /var/www/llm-audit-engine/reports
sudo chown www-data:www-data /var/www/llm-audit-engine/reports

# Run database migrations
sudo -u www-data venv/bin/alembic upgrade head

# Frontend setup
cd /var/www/llm-audit-engine/frontend
sudo -u www-data npm install
sudo -u www-data npm run build
```

## 4. Storage Strategy

### PDF Storage Structure

```
/var/www/llm-audit-engine/
├── reports/                    # PDF files stored here
│   ├── audit_{uuid}.pdf       # One PDF per audit
│   └── audit_{uuid}.html      # HTML version (optional)
└── backend/
    └── app/
        └── database (PostgreSQL)
            └── audit_outputs   # DB table with file references
```

**Key Points:**

1. **File Storage**: PDFs are stored on local disk at `/var/www/llm-audit-engine/reports/`
2. **Database Reference**: `audit_outputs` table stores `pdf_path` pointing to file
3. **Single Source of Truth**: Always query `audit_outputs` table, never access files directly
4. **Cleanup**: Automated cleanup via systemd timer (runs daily at 3 AM)
5. **Retention**: Default 30 days (configurable via `REPORTS_RETENTION_DAYS`)

### Volume/Mount for Production

For production with persistent storage:

```bash
# Create dedicated volume (if using cloud provider)
# Mount to /var/www/llm-audit-engine/reports

# Or use NFS/network storage:
sudo apt install -y nfs-common
sudo mount -t nfs nfs-server:/exports/llm-reports /var/www/llm-audit-engine/reports

# Add to /etc/fstab for persistence:
nfs-server:/exports/llm-reports /var/www/llm-audit-engine/reports nfs defaults 0 0
```

### Backup Strategy

```bash
# Daily backup of database
sudo -u postgres pg_dump llm_audit > /backup/llm-audit-$(date +%Y%m%d).sql

# Weekly backup of reports (before cleanup)
tar -czf /backup/reports-$(date +%Y%m%d).tar.gz /var/www/llm-audit-engine/reports/
```

## 5. Systemd Services

### Install services

```bash
# Copy service files
sudo cp deployment/*.service /etc/systemd/system/
sudo cp deployment/*.timer /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/llm-audit
sudo chown www-data:www-data /var/log/llm-audit

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable llm-audit-api
sudo systemctl enable llm-audit-worker
sudo systemctl enable llm-audit-cleanup.timer

sudo systemctl start llm-audit-api
sudo systemctl start llm-audit-worker
sudo systemctl start llm-audit-cleanup.timer

# Check status
sudo systemctl status llm-audit-api
sudo systemctl status llm-audit-worker
sudo systemctl list-timers llm-audit-cleanup.timer
```

## 6. Nginx Configuration

### Setup SSL

```bash
# Get SSL certificate (Let's Encrypt)
sudo certbot --nginx -d your-domain.com
```

### Configure Nginx

```bash
# Copy nginx config
sudo cp deployment/nginx.conf /etc/nginx/sites-available/llm-audit

# Edit the config and change your-domain.com
sudo nano /etc/nginx/sites-available/llm-audit

# Enable site
sudo ln -s /etc/nginx/sites-available/llm-audit /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

## 7. Monitoring & Logs

### View logs

```bash
# API logs
sudo journalctl -u llm-audit-api -f

# Worker logs
sudo journalctl -u llm-audit-worker -f
tail -f /var/log/llm-audit/worker.log

# Nginx logs
tail -f /var/log/nginx/llm-audit-access.log
tail -f /var/log/nginx/llm-audit-error.log

# Cleanup logs
sudo journalctl -u llm-audit-cleanup -f
```

### Service management

```bash
# Restart services
sudo systemctl restart llm-audit-api
sudo systemctl restart llm-audit-worker

# Check status
sudo systemctl status llm-audit-api
sudo systemctl status llm-audit-worker

# View service errors
sudo journalctl -xeu llm-audit-api
```

### Manual cleanup

```bash
# Run cleanup manually
cd /var/www/llm-audit-engine/backend
sudo -u www-data venv/bin/python -m app.cleanup
```

## 8. Firewall

```bash
# UFW firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## 9. Health Checks

### API health

```bash
curl https://your-domain.com/health
# Should return: {"status": "healthy"}
```

### Database connection

```bash
cd /var/www/llm-audit-engine/backend
sudo -u www-data venv/bin/python -c "
from app.database import engine
import asyncio
async def test():
    async with engine.connect() as conn:
        print('✓ Database connected')
asyncio.run(test())
"
```

### Storage check

```bash
# Check reports directory
ls -lh /var/www/llm-audit-engine/reports/
df -h /var/www/llm-audit-engine/reports/
```

## 10. Scaling Options

### Multiple workers

You can run multiple worker processes:

```bash
# Copy and rename service
sudo cp /etc/systemd/system/llm-audit-worker.service /etc/systemd/system/llm-audit-worker-2.service

# Enable and start
sudo systemctl enable llm-audit-worker-2
sudo systemctl start llm-audit-worker-2
```

Workers coordinate via PostgreSQL, so multiple instances are safe.

### API scaling

Edit `llm-audit-api.service` and increase `--workers`:

```ini
ExecStart=... --workers 8 ...  # Increase from 4
```

Rule of thumb: `workers = (2 * CPU cores) + 1`

## 11. Maintenance Tasks

### Weekly tasks

```bash
# Check disk space
df -h

# Check logs size
du -sh /var/log/llm-audit/
du -sh /var/log/nginx/

# Rotate logs if needed
sudo logrotate -f /etc/logrotate.d/llm-audit
```

### Monthly tasks

```bash
# Update dependencies
cd /var/www/llm-audit-engine/backend
sudo -u www-data venv/bin/pip install --upgrade -r requirements.txt

# Restart services
sudo systemctl restart llm-audit-api llm-audit-worker

# Vacuum database
sudo -u postgres psql llm_audit -c "VACUUM ANALYZE;"
```

## 12. Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -xeu llm-audit-api
sudo journalctl -xeu llm-audit-worker

# Check permissions
ls -la /var/www/llm-audit-engine/
ls -la /var/www/llm-audit-engine/reports/

# Test manually
cd /var/www/llm-audit-engine/backend
sudo -u www-data venv/bin/python -m app.worker
```

### Database issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
sudo -u postgres psql llm_audit -c "SELECT 1;"

# Reset database (CAUTION: deletes all data)
sudo -u www-data venv/bin/alembic downgrade base
sudo -u www-data venv/bin/alembic upgrade head
```

### Out of disk space

```bash
# Check usage
du -sh /var/www/llm-audit-engine/reports/

# Manual cleanup
cd /var/www/llm-audit-engine/backend
sudo -u www-data venv/bin/python -m app.cleanup

# Or delete old reports
find /var/www/llm-audit-engine/reports/ -type f -mtime +30 -delete
```

## 13. Environment Variables Reference

Required variables in `/var/www/llm-audit-engine/backend/.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/llm_audit

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Storage
REPORTS_DIR=/var/www/llm-audit-engine/reports
REPORTS_RETENTION_DAYS=30

# URLs
BACKEND_URL=https://your-domain.com
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com

# Environment
ENVIRONMENT=production
```

## 14. Security Checklist

- [ ] SSL certificate installed
- [ ] Firewall configured (UFW)
- [ ] PostgreSQL not exposed externally
- [ ] Strong database password
- [ ] OpenAI API key secured
- [ ] `.env` file permissions: `chmod 600`
- [ ] Services running as `www-data` user
- [ ] Nginx security headers configured
- [ ] Regular backups configured
- [ ] Log rotation configured

## 15. Quick Commands

```bash
# Restart everything
sudo systemctl restart llm-audit-api llm-audit-worker nginx

# View all audit services
sudo systemctl status 'llm-audit-*'

# Check disk usage
df -h && du -sh /var/www/llm-audit-engine/reports/

# Tail all logs
sudo journalctl -u llm-audit-api -u llm-audit-worker -f

# Manual audit cleanup
cd /var/www/llm-audit-engine/backend && sudo -u www-data venv/bin/python -m app.cleanup
```

## Done!

Your LLM Audit Engine is now running in production at `https://your-domain.com` 🎉

For updates, see [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).


