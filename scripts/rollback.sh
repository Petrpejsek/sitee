#!/bin/bash

# =============================================================================
# SITEE - Rollback Script
# =============================================================================
# Vrátí aplikaci na předchozí funkční verzi
#
# Použití:
#   sudo ./scripts/rollback.sh [GIT_COMMIT_HASH]
#
# Příklad:
#   sudo ./scripts/rollback.sh d557dc2
#
# Pokud nezadáte commit, vrátí se o 1 commit zpět
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
APP_DIR="/var/www/llm-audit-engine"
APP_USER="www-data"
BACKUP_DIR="/var/backups/llm-audit"
LOG_FILE="/var/log/llm-audit/rollback-$(date +%Y%m%d_%H%M%S).log"

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

# =============================================================================
# Main
# =============================================================================

log "🔙 Starting rollback..."
check_root

cd "$APP_DIR"

# Get target commit
if [ -n "$1" ]; then
    TARGET_COMMIT="$1"
    log "Rolling back to specified commit: $TARGET_COMMIT"
else
    TARGET_COMMIT=$(sudo -u $APP_USER git rev-parse HEAD~1)
    log "Rolling back to previous commit: $TARGET_COMMIT"
fi

# Verify commit exists
if ! sudo -u $APP_USER git cat-file -e "$TARGET_COMMIT^{commit}" 2>/dev/null; then
    error "Commit $TARGET_COMMIT does not exist!"
    exit 1
fi

CURRENT_COMMIT=$(sudo -u $APP_USER git rev-parse HEAD)
log "Current commit: $CURRENT_COMMIT"

# Confirm rollback
echo ""
echo -e "${YELLOW}WARNING: This will rollback from${NC}"
echo "  $CURRENT_COMMIT"
echo -e "${YELLOW}to${NC}"
echo "  $TARGET_COMMIT"
echo ""
read -p "Continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Rollback cancelled by user"
    exit 0
fi

# =============================================================================
# Step 1: Stop services
# =============================================================================

log "⏸️  Step 1/5: Stopping services..."
systemctl stop $API_SERVICE $WORKER_SERVICE
log "✓ Services stopped"

# =============================================================================
# Step 2: Git rollback
# =============================================================================

log "📥 Step 2/5: Rolling back git..."

if sudo -u $APP_USER git reset --hard "$TARGET_COMMIT"; then
    log "✓ Git rolled back to $TARGET_COMMIT"
else
    error "Git rollback failed!"
    exit 1
fi

# =============================================================================
# Step 3: Restore database (optional)
# =============================================================================

log "🗄️  Step 3/5: Checking for database backup..."

# Find latest backup
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "db-backup-*.sql.gz" | sort -r | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    echo ""
    echo -e "${YELLOW}Found backup: $LATEST_BACKUP${NC}"
    read -p "Restore database from this backup? (yes/no): " -r
    
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Restoring database..."
        gunzip -c "$LATEST_BACKUP" | sudo -u postgres psql llm_audit 2>>"$LOG_FILE"
        log "✓ Database restored"
    else
        log "Skipping database restore"
    fi
else
    warning "No database backup found, skipping restore"
fi

# =============================================================================
# Step 4: Reinstall dependencies
# =============================================================================

log "📦 Step 4/5: Reinstalling dependencies..."

cd "$APP_DIR/backend"
sudo -u $APP_USER venv/bin/pip install -r requirements.txt --quiet
log "✓ Backend dependencies installed"

cd "$APP_DIR/frontend"
sudo -u $APP_USER npm install --silent 2>>"$LOG_FILE"
sudo -u $APP_USER npm run build 2>>"$LOG_FILE"
log "✓ Frontend rebuilt"

# =============================================================================
# Step 5: Restart services
# =============================================================================

log "🔄 Step 5/5: Restarting services..."

systemctl start $API_SERVICE
systemctl start $WORKER_SERVICE

sleep 5

# Health check
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    log "✓ Health check passed"
else
    error "Health check failed (HTTP $HEALTH_CHECK)"
    exit 1
fi

# =============================================================================
# Success!
# =============================================================================

log "✅ Rollback completed successfully!"
log ""
log "Summary:"
log "  Rolled back from: $CURRENT_COMMIT"
log "  To:               $TARGET_COMMIT"
log "  Log file:         $LOG_FILE"

exit 0
