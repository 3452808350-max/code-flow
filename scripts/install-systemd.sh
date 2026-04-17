#!/bin/bash
#
# Harness Lab Systemd Service Installer
#
# Creates and installs systemd service for Harness Lab Control Plane
#
# Usage:
#   ./install-systemd.sh [--port 4600] [--install-dir /path/to/homelab]
#
# Options:
#   --port PORT         API server port (default: 4600)
#   --install-dir DIR   Installation directory (default: script's parent dir)
#   --user USER         Service user (default: current user)
#   --help              Show this help

set -e

# Defaults
API_PORT=4600
INSTALL_DIR=""
SERVICE_USER="$USER"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            API_PORT="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --user)
            SERVICE_USER="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--port PORT] [--install-dir DIR] [--user USER]"
            echo ""
            echo "Options:"
            echo "  --port PORT         API server port (default: 4600)"
            echo "  --install-dir DIR   Installation directory (default: script's parent dir)"
            echo "  --user USER         Service user (default: current user)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Determine install directory
if [ -z "$INSTALL_DIR" ]; then
    # Default to script's parent directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
fi

# Validate directory
if [ ! -d "$INSTALL_DIR" ]; then
    echo "ERROR: Install directory does not exist: $INSTALL_DIR"
    exit 1
fi

if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "ERROR: Virtual environment not found at $INSTALL_DIR/venv"
    echo "Please run bootstrap-control-plane.sh first"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_err() { echo -e "${RED}[ERR]${NC} $1"; }

# Create systemd service file
log_info "Creating systemd service file..."

sudo tee /etc/systemd/system/harness-lab.service > /dev/null << EOF
[Unit]
Description=Harness Lab Control Plane
After=network.target postgresql.service redis.service docker.service
Wants=postgresql.service redis.service docker.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR/backend
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$INSTALL_DIR/venv/bin/python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port $API_PORT
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening (optional)
# NoNewPrivileges=yes
# PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

log_ok "Service file created: /etc/systemd/system/harness-lab.service"

# Reload systemd
log_info "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
log_info "Enabling harness-lab service..."
sudo systemctl enable harness-lab

log_ok "Service enabled"

# Print summary
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Harness Lab Systemd Service Installed           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Install Dir:  $INSTALL_DIR"
echo "  API Port:     $API_PORT"
echo "  Service User: $SERVICE_USER"
echo ""
echo "Commands:"
echo "  Start:    sudo systemctl start harness-lab"
echo "  Stop:     sudo systemctl stop harness-lab"
echo "  Status:   sudo systemctl status harness-lab"
echo "  Logs:     sudo journalctl -u harness-lab -f"
echo "  Restart:  sudo systemctl restart harness-lab"
echo ""
echo "API Endpoints:"
echo "  Health:   curl http://127.0.0.1:$API_PORT/health"
echo "  Workers:  curl http://127.0.0.1:$API_PORT/api/workers"
echo "  TUI:      $INSTALL_DIR/venv/bin/hlab tui control"
echo ""