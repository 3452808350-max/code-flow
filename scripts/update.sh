#!/bin/bash
#
# Harness Lab Update Script
#
# Safely updates Harness Lab to the latest version.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/3452808350-max/Harness-Lab/main/scripts/update.sh | bash
#   ./update.sh [--check] [--force] [--backup]
#
# Options:
#   --check     Only check for updates, don't install
#   --force     Force update even if already latest
#   --backup    Create backup before updating
#   --help      Show this help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERR]${NC} $1"; }

# Defaults
CHECK_ONLY=false
FORCE=false
BACKUP=false
INSTALL_DIR="${HOME}/.harness-lab"
REPO_URL="https://github.com/3452808350-max/Harness-Lab.git"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --backup)
            BACKUP=true
            shift
            ;;
        --help)
            head -20 "$0" | tail -15
            exit 0
            ;;
        *)
            log_err "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check installation exists
check_install() {
    if [ ! -d "$INSTALL_DIR" ]; then
        log_err "Harness Lab not installed at $INSTALL_DIR"
        log_info "Run bootstrap script first:"
        echo "  curl -sSL https://raw.githubusercontent.com/3452808350-max/Harness-Lab/main/scripts/bootstrap-control-plane.sh | bash"
        exit 1
    fi
    cd "$INSTALL_DIR"
}

# Get current version
get_current_version() {
    if [ -d ".git" ]; then
        CURRENT_COMMIT=$(git rev-parse HEAD)
        CURRENT_BRANCH=$(git branch --show-current)
        CURRENT_DATE=$(git log -1 --format=%cd --date=short)
        log_info "Current: $CURRENT_BRANCH @ $CURRENT_DATE ($CURRENT_COMMIT)"
    else
        log_warn "No git repository detected"
        CURRENT_COMMIT="unknown"
    fi
}

# Get latest version from remote
get_latest_version() {
    log_info "Checking remote for updates..."
    
    # Fetch latest
    git fetch origin --quiet 2>&1 || {
        log_err "Failed to fetch from remote"
        exit 1
    }
    
    LATEST_COMMIT=$(git rev-parse origin/main)
    LATEST_DATE=$(git log -1 --format=%cd --date=short origin/main)
    
    log_info "Latest: main @ $LATEST_DATE ($LATEST_COMMIT)"
}

# Compare versions
compare_versions() {
    if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ] && [ "$FORCE" = false ]; then
        log_ok "Already on latest version!"
        if [ "$CHECK_ONLY" = true ]; then
            echo ""
            echo "  No updates available."
        fi
        exit 0
    fi
    
    if [ "$FORCE" = true ]; then
        log_warn "Force update requested"
    fi
    
    # Show diff stats
    CHANGES=$(git diff --stat HEAD origin/main)
    if [ -n "$CHANGES" ]; then
        echo ""
        echo -e "${CYAN}Changes:${NC}"
        git log --oneline HEAD..origin/main | head -10
        echo ""
        git diff --stat HEAD origin/main | tail -5
    fi
}

# Check only mode
check_mode() {
    if [ "$CHECK_ONLY" = true ]; then
        echo ""
        echo -e "${CYAN}Update available!${NC}"
        echo "  Run: ./update.sh"
        echo "  Or: curl -sSL https://raw.githubusercontent.com/3452808350-max/Harness-Lab/main/scripts/update.sh | bash"
        exit 0
    fi
}

# Create backup
create_backup() {
    if [ "$BACKUP" = true ]; then
        BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%Y%m%d%H%M%S)"
        log_info "Creating backup at $BACKUP_DIR"
        cp -r "$INSTALL_DIR" "$BACKUP_DIR"
        log_ok "Backup created"
    fi
}

# Check for breaking changes
check_breaking_changes() {
    log_info "Checking for breaking changes..."
    
    # Check if requirements changed
    if git diff --name-only HEAD origin/main | grep -q "requirements\|pyproject\|setup.py"; then
        log_warn "Dependency changes detected - will reinstall packages"
        DEPS_CHANGED=true
    fi
    
    # Check if schema changed
    if git diff --name-only HEAD origin/main | grep -q "storage.py|migrations"; then
        log_warn "Database schema changes detected - may need migration"
        SCHEMA_CHANGED=true
    fi
    
    # Check if config format changed
    if git diff --name-only HEAD origin/main | grep -q ".env.example|config"; then
        log_warn "Configuration format changes detected - check .env"
        CONFIG_CHANGED=true
    fi
}

# Pull latest code
pull_latest() {
    log_info "Pulling latest code..."
    
    # Stash local changes if any
    if [ -n "$(git status --porcelain)" ]; then
        log_warn "Local changes detected - stashing..."
        git stash push -m "pre-update stash $(date +%Y%m%d%H%M%S)"
        STASHED=true
    fi
    
    # Pull
    git pull origin main --quiet
    
    log_ok "Code updated"
}

# Update dependencies
update_deps() {
    if [ "$DEPS_CHANGED" = true ] || [ ! -d "venv" ]; then
        log_info "Updating dependencies..."
        
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        
        ./venv/bin/pip install --quiet --upgrade pip
        
        # Check if we need ML deps (has knowledge service)
        if [ -f "backend/app/harness_lab/knowledge" ]; then
            ./venv/bin/pip install --quiet \
                fastapi uvicorn pydantic pydantic-settings \
                psycopg[binary] redis python-dotenv \
                requests openai numpy sqlalchemy \
                boto3 aiofiles jinja2 \
                faiss-cpu sentence-transformers
        else
            ./venv/bin/pip install --quiet \
                fastapi uvicorn pydantic pydantic-settings \
                psycopg[binary] redis python-dotenv \
                requests openai numpy sqlalchemy \
                boto3 aiofiles jinja2
        fi
        
        log_ok "Dependencies updated"
    fi
}

# Run migrations if needed
run_migrations() {
    if [ "$SCHEMA_CHANGED" = true ]; then
        log_info "Running database migrations..."
        
        # Check for migration scripts
        if [ -d "migrations" ]; then
            ./venv/bin/python3 -m migrations.run 2>&1 || \
                log_warn "Migration may have issues - check manually"
        fi
        
        log_ok "Migrations completed"
    fi
}

# Restart services
restart_services() {
    log_info "Restarting services..."
    
    # Check if systemd service exists
    if systemctl list-unit-files | grep -q "harness-lab.service"; then
        sudo systemctl restart harness-lab
        sleep 2
        
        if systemctl is-active --quiet harness-lab; then
            log_ok "Service restarted successfully"
        else
            log_err "Service failed to restart!"
            log_info "Check logs: sudo journalctl -u harness-lab --since '1 minute ago'"
            exit 1
        fi
    else
        log_warn "No systemd service found - manual restart required"
    fi
}

# Restore stash if needed
restore_stash() {
    if [ "$STASHED" = true ]; then
        log_info "Restoring local changes..."
        git stash pop || log_warn "Could not restore stash - check manually"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              Update Complete                           ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Version: $(git log -1 --oneline)"
    echo "  Date: $(git log -1 --format=%cd --date=short)"
    echo ""
    
    if [ "$DEPS_CHANGED" = true ]; then
        echo "  Dependencies: updated"
    fi
    if [ "$SCHEMA_CHANGED" = true ]; then
        echo "  Database: migrated"
    fi
    if [ "$BACKUP" = true ]; then
        echo "  Backup: $BACKUP_DIR"
    fi
    
    echo ""
    echo "  Status: sudo systemctl status harness-lab"
    echo "  Logs:   sudo journalctl -u harness-lab -f"
    echo ""
}

# Main flow
main() {
    echo ""
    echo -e "${CYAN}=== Harness Lab Update ===${NC}"
    echo ""
    
    check_install
    get_current_version
    get_latest_version
    compare_versions
    check_mode
    create_backup
    check_breaking_changes
    pull_latest
    update_deps
    run_migrations
    restart_services
    restore_stash
    print_summary
    
    log_ok "=== Update Complete ==="
}

main