#!/bin/bash
#===============================================================================
# LLM Audit Engine - Development Control Script
# Usage: ./dev.sh [command] [options]
#===============================================================================

set -e

# Project paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOGS_DIR="$PROJECT_ROOT/logs"
REPORTS_DIR="$BACKEND_DIR/reports"

# PID files
API_PID_FILE="$LOGS_DIR/api.pid"
WORKER_PID_FILE="$LOGS_DIR/worker.pid"
FRONTEND_PID_FILE="$LOGS_DIR/frontend.pid"

# Ports
API_PORT=8000
FRONTEND_PORT=3000

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Icons
ICON_CHECK="${GREEN}✓${NC}"
ICON_CROSS="${RED}✗${NC}"
ICON_WARN="${YELLOW}⚠${NC}"
ICON_INFO="${BLUE}ℹ${NC}"
ICON_ROCKET="🚀"
ICON_STOP="🛑"
ICON_DB="🗄️"
ICON_API="⚡"
ICON_WORKER="👷"
ICON_FRONTEND="⚛️"
ICON_LOGS="📋"
ICON_HEALTH="🏥"

#===============================================================================
# Helper Functions
#===============================================================================

print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}LLM Audit Engine${NC} - 2-Stage Pipeline (v2.0)               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}LLM Traffic / GEO / Citability Analysis${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_help() {
    print_banner
    echo -e "${BOLD}Usage:${NC} ./dev.sh [command] [options]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}start${NC}         Start all services (full setup)"
    echo -e "  ${GREEN}stop${NC}          Stop all services"
    echo -e "  ${GREEN}restart${NC}       Restart all services (quick)"
    echo -e "  ${RED}kill-all${NC}      Aggressively kill all dev processes (use when stuck)"
    echo -e "  ${GREEN}status${NC}        Show status of all services"
    echo ""
    echo -e "  ${YELLOW}api${NC}           Manage API server"
    echo -e "    ${DIM}start${NC}       Start API server"
    echo -e "    ${DIM}stop${NC}        Stop API server"
    echo -e "    ${DIM}restart${NC}     Restart API server"
    echo -e "    ${DIM}logs${NC}        Tail API logs"
    echo ""
    echo -e "  ${YELLOW}worker${NC}        Manage background worker"
    echo -e "    ${DIM}start${NC}       Start worker"
    echo -e "    ${DIM}stop${NC}        Stop worker"
    echo -e "    ${DIM}restart${NC}     Restart worker"
    echo -e "    ${DIM}logs${NC}        Tail worker logs"
    echo ""
    echo -e "  ${YELLOW}frontend${NC}      Manage frontend dev server"
    echo -e "    ${DIM}start${NC}       Start frontend"
    echo -e "    ${DIM}stop${NC}        Stop frontend"
    echo -e "    ${DIM}restart${NC}     Restart frontend"
    echo -e "    ${DIM}logs${NC}        Tail frontend logs"
    echo ""
    echo -e "  ${YELLOW}db${NC}            Manage PostgreSQL database"
    echo -e "    ${DIM}start${NC}       Start database"
    echo -e "    ${DIM}stop${NC}        Stop database"
    echo -e "    ${DIM}restart${NC}     Restart database"
    echo -e "    ${DIM}migrate${NC}     Run Alembic migrations"
    echo -e "    ${DIM}shell${NC}       Open psql shell"
    echo -e "    ${DIM}reset${NC}       Reset database (destructive!)"
    echo ""
    echo -e "  ${BLUE}logs${NC}          Tail all logs (combined)"
    echo -e "  ${BLUE}logs api${NC}      Tail API logs only"
    echo -e "  ${BLUE}logs worker${NC}   Tail worker logs only"
    echo -e "  ${BLUE}logs frontend${NC} Tail frontend logs only"
    echo ""
    echo -e "  ${MAGENTA}test${NC}          Run tests"
    echo -e "  ${MAGENTA}lint${NC}          Run linters"
    echo -e "  ${MAGENTA}clean${NC}         Clean up temp files & old reports"
    echo -e "  ${MAGENTA}setup${NC}         Initial setup (venv, npm install, etc.)"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./dev.sh start              # Full startup"
    echo "  ./dev.sh restart            # Quick restart"
    echo "  ./dev.sh worker restart     # Restart only worker"
    echo "  ./dev.sh logs               # Tail all logs"
    echo "  ./dev.sh db migrate         # Run migrations"
    echo "  ./dev.sh status             # Check what's running"
    echo ""
}

ensure_dirs() {
    mkdir -p "$LOGS_DIR"
    mkdir -p "$REPORTS_DIR"
}

check_port() {
    local port=$1
    lsof -ti:$port &>/dev/null
}

kill_port() {
    local port=$1
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
}

get_pid_from_file() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        cat "$pid_file" 2>/dev/null
    fi
}

is_process_running() {
    local pid=$1
    [ -n "$pid" ] && ps -p "$pid" &>/dev/null
}

wait_for_port() {
    local port=$1
    local max_wait=${2:-30}
    local counter=0
    
    while ! check_port $port; do
        sleep 1
        counter=$((counter + 1))
        if [ $counter -ge $max_wait ]; then
            return 1
        fi
    done
    return 0
}

activate_venv() {
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        echo -e "${ICON_WARN} Virtual environment not found. Run ${CYAN}./dev.sh setup${NC} first."
        exit 1
    fi
    source "$BACKEND_DIR/venv/bin/activate"
}

#===============================================================================
# Config Validation
#===============================================================================

validate_config() {
    echo -e "${ICON_INFO} Validating configuration..."
    
    # Check .env file
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        echo -e "${ICON_WARN} .env file not found"
        if [ -f "$PROJECT_ROOT/env.example" ]; then
            cp "$PROJECT_ROOT/env.example" "$BACKEND_DIR/.env"
            echo -e "${ICON_CROSS} Created .env from template. ${RED}Edit backend/.env and add OPENAI_API_KEY${NC}"
            exit 1
        else
            echo -e "${ICON_CROSS} env.example not found!"
            exit 1
        fi
    fi
    
    # Validate LLM key
    if grep -q "sk-CHANGE-THIS-TO-YOUR-REAL-KEY" "$BACKEND_DIR/.env" 2>/dev/null; then
        echo -e "${ICON_CROSS} ${RED}OPENAI_API_KEY not configured!${NC}"
        echo "Edit backend/.env and set your real API key"
        exit 1
    fi
    
    # Determine provider (optional)
    local provider=""
    provider=$(grep -E "^LLM_PROVIDER=" "$BACKEND_DIR/.env" 2>/dev/null | tail -1 | cut -d'=' -f2 | tr -d '\r')
    local base_url=""
    base_url=$(grep -E "^OPENAI_BASE_URL=" "$BACKEND_DIR/.env" 2>/dev/null | tail -1 | cut -d'=' -f2 | tr -d '\r')

    if [ "$provider" = "openrouter" ] || echo "$base_url" | grep -qi "openrouter.ai"; then
        if ! grep -qE "^OPENAI_API_KEY=sk-or-" "$BACKEND_DIR/.env" 2>/dev/null; then
            echo -e "${ICON_CROSS} ${RED}OPENAI_API_KEY missing or invalid for OpenRouter${NC}"
            echo "Expected OPENAI_API_KEY to start with 'sk-or-' when using OpenRouter."
            exit 1
        fi
    else
        if ! grep -qE "^OPENAI_API_KEY=sk-" "$BACKEND_DIR/.env" 2>/dev/null; then
            echo -e "${ICON_CROSS} ${RED}OPENAI_API_KEY missing or invalid for OpenAI${NC}"
            echo "Expected OPENAI_API_KEY to start with 'sk-' when using OpenAI."
            exit 1
        fi
    fi
    
    echo -e "${ICON_CHECK} Configuration OK"
}

#===============================================================================
# Database Functions
#===============================================================================

db_start() {
    echo -e "${ICON_DB} Starting PostgreSQL..."
    
    if ! command -v docker &>/dev/null; then
        echo -e "${ICON_CROSS} Docker not found. Install Docker Desktop."
        exit 1
    fi
    
    if ! docker info &>/dev/null; then
        echo -e "${ICON_CROSS} Docker is not running. Start Docker Desktop."
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    docker-compose up -d postgres
    
    # Wait for DB
    echo -e "${DIM}Waiting for database...${NC}"
    local counter=0
    until docker-compose exec -T postgres pg_isready -U postgres -d llm_audit &>/dev/null; do
        sleep 1
        counter=$((counter + 1))
        if [ $counter -ge 30 ]; then
            echo -e "${ICON_CROSS} Database failed to start"
            docker-compose logs postgres
            exit 1
        fi
    done
    
    echo -e "${ICON_CHECK} PostgreSQL ready"
}

db_stop() {
    echo -e "${ICON_DB} Stopping PostgreSQL..."
    cd "$PROJECT_ROOT"
    docker-compose stop postgres 2>/dev/null || true
    echo -e "${ICON_CHECK} PostgreSQL stopped"
}

db_restart() {
    db_stop
    sleep 1
    db_start
}

db_migrate() {
    echo -e "${ICON_DB} Running migrations..."
    activate_venv
    cd "$BACKEND_DIR"
    alembic upgrade head
    echo -e "${ICON_CHECK} Migrations complete"
}

db_shell() {
    echo -e "${ICON_DB} Opening PostgreSQL shell..."
    cd "$PROJECT_ROOT"
    docker-compose exec postgres psql -U postgres -d llm_audit
}

db_reset() {
    echo -e "${RED}${BOLD}⚠️  WARNING: This will DELETE ALL DATA!${NC}"
    read -p "Are you sure? Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
    
    echo -e "${ICON_DB} Resetting database..."
    cd "$PROJECT_ROOT"
    docker-compose down -v postgres 2>/dev/null || true
    docker-compose up -d postgres
    sleep 5
    db_migrate
    echo -e "${ICON_CHECK} Database reset complete"
}

#===============================================================================
# API Functions
#===============================================================================

api_start() {
    echo -e "${ICON_API} Starting API server..."
    ensure_dirs
    activate_venv
    
    # Kill existing
    kill_port $API_PORT
    
    cd "$BACKEND_DIR"
    uvicorn app.main:app --reload --port $API_PORT --log-level info > "$LOGS_DIR/api.log" 2>&1 &
    local pid=$!
    echo $pid > "$API_PID_FILE"
    
    # Wait for startup
    sleep 2
    if is_process_running $pid; then
        echo -e "${ICON_CHECK} API server started (PID: $pid)"
        echo -e "    ${DIM}http://localhost:$API_PORT${NC}"
    else
        echo -e "${ICON_CROSS} API failed to start. Check logs/api.log"
        exit 1
    fi
}

api_stop() {
    echo -e "${ICON_API} Stopping API server..."
    
    local pid=$(get_pid_from_file "$API_PID_FILE")
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || true
        rm -f "$API_PID_FILE"
    fi
    
    kill_port $API_PORT
    echo -e "${ICON_CHECK} API server stopped"
}

api_restart() {
    api_stop
    sleep 1
    api_start
}

api_logs() {
    echo -e "${ICON_LOGS} API logs (Ctrl+C to exit):"
    tail -f "$LOGS_DIR/api.log"
}

#===============================================================================
# Worker Functions
#===============================================================================

worker_start() {
    echo -e "${ICON_WORKER} Starting worker..."
    ensure_dirs
    activate_venv
    
    # FORCE kill ALL existing workers first (reliable cleanup)
    worker_stop_force
    sleep 1
    
    cd "$BACKEND_DIR"
    python -m app.worker > "$LOGS_DIR/worker.log" 2>&1 &
    local pid=$!
    
    sleep 3
    if is_process_running $pid; then
        echo -e "${ICON_CHECK} Worker started (PID: $pid)"
        echo -e "    ${DIM}2-Stage Pipeline: Stage A (Core Audit) + Stage B (Action Plan)${NC}"
    else
        echo -e "${ICON_CROSS} Worker failed to start. Check logs/worker.log"
        tail -20 "$LOGS_DIR/worker.log" 2>/dev/null
        exit 1
    fi
}

worker_stop_force() {
    # Kill by PID file
    if [ -f "$WORKER_PID_FILE" ]; then
        local pid=$(cat "$WORKER_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ]; then
            kill -9 $pid 2>/dev/null || true
        fi
        rm -f "$WORKER_PID_FILE"
    fi
    
    # Kill ALL worker processes by pattern (aggressive)
    pkill -9 -f "python.*app.worker" 2>/dev/null || true
    pkill -9 -f "python -m app.worker" 2>/dev/null || true
    
    # Also clean up any stray python processes in backend dir
    pgrep -f "python.*app/worker" | xargs kill -9 2>/dev/null || true
}

worker_stop() {
    echo -e "${ICON_WORKER} Stopping worker..."
    worker_stop_force
    echo -e "${ICON_CHECK} Worker stopped"
}

worker_restart() {
    worker_stop
    sleep 1
    worker_start
}

worker_logs() {
    echo -e "${ICON_LOGS} Worker logs (Ctrl+C to exit):"
    tail -f "$LOGS_DIR/worker.log"
}

#===============================================================================
# Frontend Functions
#===============================================================================

frontend_start() {
    echo -e "${ICON_FRONTEND} Starting frontend..."
    ensure_dirs
    
    # Kill existing
    kill_port $FRONTEND_PORT
    
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        echo -e "${ICON_WARN} node_modules not found. Run ${CYAN}./dev.sh setup${NC} first."
        exit 1
    fi
    
    npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"
    
    sleep 3
    if is_process_running $pid; then
        echo -e "${ICON_CHECK} Frontend started (PID: $pid)"
        echo -e "    ${DIM}http://localhost:$FRONTEND_PORT${NC}"
    else
        echo -e "${ICON_CROSS} Frontend failed to start. Check logs/frontend.log"
        exit 1
    fi
}

frontend_stop() {
    echo -e "${ICON_FRONTEND} Stopping frontend..."
    
    local pid=$(get_pid_from_file "$FRONTEND_PID_FILE")
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || true
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    kill_port $FRONTEND_PORT
    echo -e "${ICON_CHECK} Frontend stopped"
}

frontend_restart() {
    frontend_stop
    sleep 1
    frontend_start
}

frontend_logs() {
    echo -e "${ICON_LOGS} Frontend logs (Ctrl+C to exit):"
    tail -f "$LOGS_DIR/frontend.log"
}

#===============================================================================
# Combined Functions
#===============================================================================

start_all() {
    print_banner
    validate_config
    ensure_dirs
    
    echo ""
    db_start
    
    echo ""
    setup_backend_if_needed
    db_migrate
    
    echo ""
    api_start
    
    echo ""
    worker_start
    
    echo ""
    setup_frontend_if_needed
    frontend_start
    
    echo ""
    show_status
    
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}${BOLD}✅ LLM Audit Engine is running!${NC}                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}Open:${NC}  ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  ${BOLD}API:${NC}   ${DIM}http://localhost:$API_PORT${NC}"
    echo ""
    echo -e "  ${BOLD}Logs:${NC}  ./dev.sh logs"
    echo -e "  ${BOLD}Stop:${NC}  ./dev.sh stop"
    echo ""
}

stop_all() {
    print_banner
    echo -e "${ICON_STOP} Stopping all services..."
    echo ""
    
    frontend_stop
    worker_stop
    api_stop
    db_stop
    
    echo ""
    echo -e "${ICON_CHECK} ${GREEN}All services stopped${NC}"
}

kill_all() {
    print_banner
    echo -e "${RED}${BOLD}🧨 Kill-all: force stopping everything (ports + stray processes)${NC}"
    echo ""

    # Stop via normal paths first (safe)
    frontend_stop || true
    worker_stop_force || true
    api_stop || true

    # Ensure ports are free
    kill_port $API_PORT || true
    kill_port $FRONTEND_PORT || true

    # Kill any strays by pattern (aggressive)
    pkill -9 -f "uvicorn .*app\\.main:app" 2>/dev/null || true
    pkill -9 -f "python.*uvicorn" 2>/dev/null || true
    pkill -9 -f "npm run dev" 2>/dev/null || true
    pkill -9 -f "vite" 2>/dev/null || true
    pkill -9 -f "python.*app\\.worker" 2>/dev/null || true
    pkill -9 -f "python -m app\\.worker" 2>/dev/null || true

    # Remove PID files
    rm -f "$API_PID_FILE" "$WORKER_PID_FILE" "$FRONTEND_PID_FILE" 2>/dev/null || true

    # Stop DB container too (optional but requested as "kill-all")
    cd "$PROJECT_ROOT"
    docker-compose stop postgres 2>/dev/null || true

    echo ""
    echo -e "${ICON_CHECK} ${GREEN}Kill-all complete${NC}"
    echo -e "  Next: ${CYAN}./dev.sh start${NC} or ${CYAN}./dev.sh restart${NC}"
}

restart_all() {
    print_banner
    echo -e "${ICON_ROCKET} Quick restart..."
    echo ""
    
    # Stop services (but keep DB running)
    frontend_stop
    worker_stop
    api_stop
    
    sleep 1
    
    # Check DB is running
    if ! docker-compose exec -T postgres pg_isready -U postgres -d llm_audit &>/dev/null 2>&1; then
        db_start
    fi
    
    # Restart services
    api_start
    echo ""
    worker_start
    echo ""
    frontend_start
    
    echo ""
    echo -e "${ICON_CHECK} ${GREEN}Services restarted${NC}"
    echo -e "  ${BOLD}Open:${NC}  ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
}

show_status() {
    echo -e "${ICON_HEALTH} ${BOLD}Service Status:${NC}"
    echo ""
    
    # Database
    if docker-compose exec -T postgres pg_isready -U postgres -d llm_audit &>/dev/null 2>&1; then
        echo -e "  ${ICON_DB} PostgreSQL    ${GREEN}● running${NC}"
    else
        echo -e "  ${ICON_DB} PostgreSQL    ${RED}○ stopped${NC}"
    fi
    
    # API
    local api_pid=$(get_pid_from_file "$API_PID_FILE")
    if is_process_running "$api_pid" || check_port $API_PORT; then
        local health=$(curl -s http://localhost:$API_PORT/health 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$health" = "healthy" ]; then
            echo -e "  ${ICON_API} API Server    ${GREEN}● running${NC} (http://localhost:$API_PORT)"
        else
            echo -e "  ${ICON_API} API Server    ${YELLOW}● starting${NC}"
        fi
    else
        echo -e "  ${ICON_API} API Server    ${RED}○ stopped${NC}"
    fi
    
    # Worker
    local worker_pid=$(get_pid_from_file "$WORKER_PID_FILE")
    if is_process_running "$worker_pid" || pgrep -f "python -m app.worker" &>/dev/null; then
        echo -e "  ${ICON_WORKER} Worker        ${GREEN}● running${NC} (2-Stage Pipeline)"
    else
        echo -e "  ${ICON_WORKER} Worker        ${RED}○ stopped${NC}"
    fi
    
    # Frontend
    local frontend_pid=$(get_pid_from_file "$FRONTEND_PID_FILE")
    if is_process_running "$frontend_pid" || check_port $FRONTEND_PORT; then
        echo -e "  ${ICON_FRONTEND} Frontend      ${GREEN}● running${NC} (http://localhost:$FRONTEND_PORT)"
    else
        echo -e "  ${ICON_FRONTEND} Frontend      ${RED}○ stopped${NC}"
    fi
    
    echo ""
}

show_logs() {
    local service=$1
    
    case "$service" in
        api)
            api_logs
            ;;
        worker)
            worker_logs
            ;;
        frontend)
            frontend_logs
            ;;
        *)
            echo -e "${ICON_LOGS} All logs (Ctrl+C to exit):"
            tail -f "$LOGS_DIR/api.log" "$LOGS_DIR/worker.log" "$LOGS_DIR/frontend.log" 2>/dev/null
            ;;
    esac
}

#===============================================================================
# Setup Functions
#===============================================================================

setup_backend_if_needed() {
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        echo -e "${ICON_INFO} Setting up Python backend..."
        cd "$BACKEND_DIR"
        python3 -m venv venv
        source venv/bin/activate
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
        echo -e "${ICON_CHECK} Backend setup complete"
    fi
}

setup_frontend_if_needed() {
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${ICON_INFO} Installing frontend dependencies..."
        cd "$FRONTEND_DIR"
        npm install --silent
        echo -e "${ICON_CHECK} Frontend setup complete"
    fi
}

full_setup() {
    print_banner
    echo -e "${ICON_ROCKET} Full setup..."
    echo ""
    
    validate_config
    ensure_dirs
    
    # Backend
    echo -e "${ICON_INFO} Setting up Python backend..."
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${ICON_CHECK} Backend dependencies installed"
    
    # Frontend
    echo ""
    echo -e "${ICON_INFO} Setting up frontend..."
    cd "$FRONTEND_DIR"
    
    if [ -d "node_modules" ]; then
        rm -rf node_modules
    fi
    
    npm install
    echo -e "${ICON_CHECK} Frontend dependencies installed"
    
    # Database
    echo ""
    db_start
    db_migrate
    
    echo ""
    echo -e "${ICON_CHECK} ${GREEN}Setup complete!${NC}"
    echo -e "  Run ${CYAN}./dev.sh start${NC} to start all services"
}

clean() {
    echo -e "${ICON_INFO} Cleaning up..."
    
    # Remove old reports (older than 7 days)
    find "$REPORTS_DIR" -name "*.pdf" -mtime +7 -delete 2>/dev/null || true
    find "$REPORTS_DIR" -name "*.html" -mtime +7 -delete 2>/dev/null || true
    
    # Remove Python cache
    find "$BACKEND_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$BACKEND_DIR" -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove logs older than 7 days
    find "$LOGS_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    echo -e "${ICON_CHECK} Cleanup complete"
}

run_tests() {
    echo -e "${ICON_INFO} Running tests..."
    activate_venv
    cd "$BACKEND_DIR"
    
    if [ -f "pytest.ini" ] || [ -d "tests" ]; then
        pytest
    else
        echo -e "${ICON_WARN} No tests found"
    fi
}

run_lint() {
    echo -e "${ICON_INFO} Running linters..."
    activate_venv
    cd "$BACKEND_DIR"
    
    echo "Checking Python..."
    if command -v ruff &>/dev/null; then
        ruff check app/
    elif command -v flake8 &>/dev/null; then
        flake8 app/
    else
        echo -e "${ICON_WARN} No Python linter found (install ruff or flake8)"
    fi
    
    echo ""
    echo "Checking frontend..."
    cd "$FRONTEND_DIR"
    if [ -f "package.json" ] && grep -q "lint" package.json; then
        npm run lint 2>/dev/null || true
    fi
    
    echo -e "${ICON_CHECK} Linting complete"
}

#===============================================================================
# Main Command Handler
#===============================================================================

cd "$PROJECT_ROOT"

case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    kill-all|killall)
        kill_all
        ;;
    status)
        print_banner
        show_status
        ;;
    
    # API commands
    api)
        case "${2:-start}" in
            start)   api_start ;;
            stop)    api_stop ;;
            restart) api_restart ;;
            logs)    api_logs ;;
            *)       echo "Usage: ./dev.sh api [start|stop|restart|logs]" ;;
        esac
        ;;
    
    # Worker commands
    worker)
        case "${2:-start}" in
            start)   worker_start ;;
            stop)    worker_stop ;;
            restart) worker_restart ;;
            logs)    worker_logs ;;
            *)       echo "Usage: ./dev.sh worker [start|stop|restart|logs]" ;;
        esac
        ;;
    
    # Frontend commands
    frontend)
        case "${2:-start}" in
            start)   frontend_start ;;
            stop)    frontend_stop ;;
            restart) frontend_restart ;;
            logs)    frontend_logs ;;
            *)       echo "Usage: ./dev.sh frontend [start|stop|restart|logs]" ;;
        esac
        ;;
    
    # Database commands
    db)
        case "${2:-}" in
            start)   db_start ;;
            stop)    db_stop ;;
            restart) db_restart ;;
            migrate) db_migrate ;;
            shell)   db_shell ;;
            reset)   db_reset ;;
            *)       echo "Usage: ./dev.sh db [start|stop|restart|migrate|shell|reset]" ;;
        esac
        ;;
    
    # Logs
    logs)
        show_logs "${2:-}"
        ;;
    
    # Utilities
    setup)
        full_setup
        ;;
    clean)
        clean
        ;;
    test)
        run_tests
        ;;
    lint)
        run_lint
        ;;
    
    # Help
    help|--help|-h|"")
        print_help
        ;;
    
    *)
        echo -e "${ICON_CROSS} Unknown command: $1"
        echo "Run ${CYAN}./dev.sh help${NC} for usage"
        exit 1
        ;;
esac
