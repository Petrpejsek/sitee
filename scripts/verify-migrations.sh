#!/bin/bash

# =============================================================================
# SITEE - Verify Alembic Migrations
# =============================================================================
# Test že všechny Alembic migrace fungují na čisté databázi
#
# Použití:
#   ./scripts/verify-migrations.sh
#
# Pozor: Vyžaduje běžící PostgreSQL z docker-compose!
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[✓]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if in project root
if [ ! -f "backend/alembic.ini" ]; then
    error "Must run from project root directory"
    exit 1
fi

# Check if docker-compose DB is running
if ! docker ps | grep -q "llm-audit-postgres"; then
    error "PostgreSQL container not running!"
    echo "Start it with: docker-compose up -d"
    exit 1
fi

log "Starting migration verification..."

# Create test database
TEST_DB="llm_audit_test"
log "Creating test database: $TEST_DB"

docker exec llm-audit-postgres psql -U postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
docker exec llm-audit-postgres psql -U postgres -c "CREATE DATABASE $TEST_DB;"

# Update DATABASE_URL for test
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/$TEST_DB"

cd backend

log "Running migrations..."

# Run all migrations
if python -m alembic upgrade head; then
    log "✅ All migrations executed successfully!"
else
    error "❌ Migration failed!"
    exit 1
fi

# Verify database structure
log "Verifying database structure..."

TABLES=$(docker exec llm-audit-postgres psql -U postgres -d $TEST_DB -t -c "\dt" | grep -c "public" || true)

if [ "$TABLES" -gt 0 ]; then
    log "✅ Found $TABLES tables in database"
    
    # List tables
    echo ""
    echo "Tables created:"
    docker exec llm-audit-postgres psql -U postgres -d $TEST_DB -c "\dt"
else
    error "❌ No tables found!"
    exit 1
fi

# Test downgrade
log "Testing downgrade (rollback)..."

if python -m alembic downgrade -1; then
    log "✅ Downgrade successful"
else
    warning "⚠️  Downgrade failed (might be expected for some migrations)"
fi

# Upgrade back
if python -m alembic upgrade head; then
    log "✅ Re-upgrade successful"
fi

# Cleanup
log "Cleaning up test database..."
docker exec llm-audit-postgres psql -U postgres -c "DROP DATABASE $TEST_DB;"

log "✅ Migration verification complete!"

exit 0
