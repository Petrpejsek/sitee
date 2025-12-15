#!/bin/bash

# =============================================================================
# SITEE - Production Deployment Script
# =============================================================================
# Automatizovaný deployment script pro produkční server
#
# Použití:
#   sudo ./scripts/deploy.sh
#
# Co dělá:
#   1. Backup databáze
#   2. Pull z GitHub (main větev)
#   3. Install/update dependencies
#   4. Run Alembic migrations
#   5. Rebuild frontend (pokud změněn)
#   6. Restart služeb
#   7. Health check
#   8. Rollback při chybě
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/var/www/llm-audit-engine"
APP_USER="www-data"
BACKUP_DIR="/var/backups/llm-audit"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/llm-audit/deploy-${TIMESTAMP}.log"

# Service names
API_SERVICE="llm-audit-api"
WORKER_SERVICE="llm-audit-worker"

# =============================================================================
# Helper Functions
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        error "Please run as root (use sudo)"
        exit 1
    fi
}

check_dir() {
    if [ ! -d "$APP_DIR" ]; then
        error "Application directory not found: $APP_DIR"
        exit 1
    fi
}

# =============================================================================
# Pre-deployment Checks
# =============================================================================

log "🚀 Starting deployment..."
check_root
check_dir

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

cd "$APP_DIR"

# Save current git commit for rollback
CURRENT_COMMIT=$(sudo -u $APP_USER git rev-parse HEAD)
log "Current commit: $CURRENT_COMMIT"

# =============================================================================
# Step 1: Backup Database
# =============================================================================

log "📦 Step 1/7: Creating database backup..."
BACKUP_FILE="$BACKUP_DIR/db-backup-${TIMESTAMP}.sql"

if sudo -u postgres pg_dump llm_audit > "$BACKUP_FILE" 2>>"$LOG_FILE"; then
    log "✓ Database backed up to: $BACKUP_FILE"
    gzip "$BACKUP_FILE"
    log "✓ Backup compressed: ${BACKUP_FILE}.gz"
else
    error "Database backup failed!"
    exit 1
fi

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "db-backup-*.sql.gz" -mtime +7 -delete
log "✓ Old backups cleaned up"

# =============================================================================
# Step 2: Pull from GitHub
# =============================================================================

log "📥 Step 2/7: Pulling latest code from GitHub..."

if sudo -u $APP_USER git fetch origin; then
    log "✓ Fetched from GitHub"
else
    error "Git fetch failed!"
    exit 1
fi

# Check if there are changes
LOCAL=$(sudo -u $APP_USER git rev-parse main)
REMOTE=$(sudo -u $APP_USER git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    warning "No new changes to deploy. Exiting..."
    exit 0
fi

log "Pulling changes..."
if sudo -u $APP_USER git pull origin main; then
    NEW_COMMIT=$(sudo -u $APP_USER git rev-parse HEAD)
    log "✓ Pulled successfully. New commit: $NEW_COMMIT"
else
    error "Git pull failed!"
    exit 1
fi

# =============================================================================
# Step 3: Update Backend Dependencies
# =============================================================================

log "🐍 Step 3/7: Updating backend dependencies..."

cd "$APP_DIR/backend"

if sudo -u $APP_USER venv/bin/pip install -r requirements.txt --quiet; then
    log "✓ Backend dependencies updated"
else
    error "Failed to update backend dependencies!"
    exit 1
fi

# =============================================================================
# Step 4: Run Database Migrations
# =============================================================================

log "🗄️  Step 4/7: Running database migrations..."

if sudo -u $APP_USER venv/bin/alembic upgrade head 2>>"$LOG_FILE"; then
    log "✓ Migrations completed"
else
    error "Migrations failed! Rolling back..."
    sudo -u postgres psql llm_audit < "$BACKUP_FILE"
    error "Database restored from backup"
    exit 1
fi

# =============================================================================
# Step 5: Rebuild Frontend (if changed)
# =============================================================================

log "⚛️  Step 5/7: Checking frontend changes..."

cd "$APP_DIR/frontend"

# Check if frontend files changed
if git diff --name-only "$CURRENT_COMMIT" "$NEW_COMMIT" | grep -q "^frontend/"; then
    log "Frontend changed, rebuilding..."
    
    if sudo -u $APP_USER npm install --silent; then
        log "✓ Frontend dependencies installed"
    else
        warning "Frontend npm install had warnings, continuing..."
    fi
    
    if sudo -u $APP_USER npm run build; then
        log "✓ Frontend built successfully"
    else
        error "Frontend build failed!"
        exit 1
    fi
else
    log "✓ No frontend changes, skipping rebuild"
fi

# =============================================================================
# Step 6: Restart Services
# =============================================================================

log "🔄 Step 6/7: Restarting services..."

# Restart API
if systemctl restart $API_SERVICE; then
    log "✓ $API_SERVICE restarted"
else
    error "Failed to restart $API_SERVICE"
    exit 1
fi

# Restart Worker
if systemctl restart $WORKER_SERVICE; then
    log "✓ $WORKER_SERVICE restarted"
else
    warning "Failed to restart $WORKER_SERVICE"
fi

# Wait for services to start
sleep 5

# =============================================================================
# Step 7: Health Check
# =============================================================================

log "🏥 Step 7/7: Running health check..."

# Try health check endpoint
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    log "✓ Health check passed (HTTP $HEALTH_CHECK)"
else
    error "Health check failed (HTTP $HEALTH_CHECK)"
    error "Rolling back to previous version..."
    
    # Rollback git
    cd "$APP_DIR"
    sudo -u $APP_USER git reset --hard "$CURRENT_COMMIT"
    
    # Restore database
    gunzip -c "${BACKUP_FILE}.gz" | sudo -u postgres psql llm_audit
    
    # Restart services
    systemctl restart $API_SERVICE $WORKER_SERVICE
    
    error "Rollback completed. Check logs: $LOG_FILE"
    exit 1
fi

# =============================================================================
# Success!
# =============================================================================

log "✅ Deployment completed successfully!"
log ""
log "Summary:"
log "  Previous commit: $CURRENT_COMMIT"
log "  New commit:      $NEW_COMMIT"
log "  Backup:          ${BACKUP_FILE}.gz"
log "  Log file:        $LOG_FILE"
log ""
log "Next steps:"
log "  1. Test the application: curl https://YOUR_DOMAIN/health"
log "  2. Monitor logs: journalctl -u $API_SERVICE -f"
log "  3. Check worker: journalctl -u $WORKER_SERVICE -f"

# Send notification (optional)
# curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
#   -d "{\"text\":\"✅ Sitee deployed successfully: $NEW_COMMIT\"}"

exit 0
