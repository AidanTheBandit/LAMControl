#!/bin/bash
"""
LAMControl Server Installation Script

This script installs the LAMControl distributed server that orchestrates worker nodes.
"""

set -e

# Default values
SERVER_HOST="0.0.0.0"
SERVER_PORT="8080"
GROQ_API_KEY=""
INSTALL_DIR="$HOME/lamcontrol-server"
PYTHON_CMD="python3"
SERVICE_NAME="lamcontrol-server"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
LAMControl Server Installation Script

This script installs and configures the LAMControl distributed server
that orchestrates worker nodes with pluggable integrations.

Usage: $0 [OPTIONS]

OPTIONS:
    --server-host HOST        Server bind address (default: 0.0.0.0)
    --server-port PORT        Server port (default: 8080)
    --groq-api-key KEY        GROQ API key for LLM processing
    --install-dir DIR         Installation directory (default: ~/lamcontrol-server)
    --python-cmd CMD          Python command to use (default: python3)
    --service-name NAME       Systemd service name (default: lamcontrol-server)
    --help                    Show this help message

EXAMPLES:
    # Basic installation
    $0 --groq-api-key "your-groq-api-key-here"
    
    # Custom port and host
    $0 --groq-api-key "your-key" --server-port 5000 --server-host 192.168.1.100
    
    # Install in custom directory
    $0 --groq-api-key "your-key" --install-dir "/opt/lamcontrol"

AFTER INSTALLATION:
    The server will be available at http://your-server-ip:port
    - Admin UI: http://your-server-ip:port/admin
    - R1 Client: http://your-server-ip:port/r1
    - API: http://your-server-ip:port/api
    
    Worker nodes can register to this server and install integrations dynamically.
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server-host)
                SERVER_HOST="$2"
                shift 2
                ;;
            --server-port)
                SERVER_PORT="$2"
                shift 2
                ;;
            --groq-api-key)
                GROQ_API_KEY="$2"
                shift 2
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --python-cmd)
                PYTHON_CMD="$2"
                shift 2
                ;;
            --service-name)
                SERVICE_NAME="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python not found. Please install Python 3.8 or later."
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l) ]]; then
        print_error "Python 3.8 or later is required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION found"
    
    # Check pip
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_error "pip not found. Please install pip."
        exit 1
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        print_error "git not found. Please install git."
        exit 1
    fi
    
    # Check GROQ API key
    if [ -z "$GROQ_API_KEY" ]; then
        print_error "GROQ API key is required. Use --groq-api-key option."
        print_status "Get your API key at: https://console.groq.com/keys"
        exit 1
    fi
    
    print_success "System requirements satisfied"
}

install_server() {
    print_status "Installing LAMControl server..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Clone or update repository
    if [ -d ".git" ]; then
        print_status "Updating existing installation..."
        git pull origin main
    else
        print_status "Cloning LAMControl repository..."
        git clone https://github.com/AidanTheBandit/LAMControl.git .
    fi
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    $PYTHON_CMD -m pip install --user -r requirements_distributed.txt
    
    print_success "LAMControl server installed"
}

create_configuration() {
    print_status "Creating server configuration..."
    
    # Create configuration file
    cat > config.json << EOF
{
  "mode": "distributed_server",
  "debug": false,
  "cache_dir": "cache",
  "groq_model": "llama-3.3-70b-versatile",
  "distributed": {
    "server_host": "$SERVER_HOST",
    "server_port": $SERVER_PORT,
    "worker_timeout": 30,
    "max_workers": 50,
    "heartbeat_interval": 30
  },
  "security": {
    "require_auth": true,
    "session_timeout": 3600
  },
  "logging": {
    "level": "INFO",
    "file": "lamcontrol.log"
  }
}
EOF
    
    # Create environment file
    cat > .env << EOF
# LAMControl Server Environment Variables
GROQ_API_KEY=$GROQ_API_KEY

# Optional: Additional API keys for integrations
# DISCORD_BOT_TOKEN=your_discord_bot_token
# TELEGRAM_BOT_TOKEN=your_telegram_bot_token
# OPENAI_API_KEY=your_openai_api_key
EOF
    
    print_success "Configuration created"
}

create_service_files() {
    print_status "Creating service files..."
    
    # Create startup script
    cat > start_server.sh << EOF
#!/bin/bash
cd "$INSTALL_DIR"
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
$PYTHON_CMD distributed_server.py
EOF
    chmod +x start_server.sh
    
    # Create systemd service file
    cat > ${SERVICE_NAME}.service << EOF
[Unit]
Description=LAMControl Distributed Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(groups | cut -d' ' -f1)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/start_server.sh
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONPATH=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Service files created"
}

setup_firewall() {
    print_status "Configuring firewall..."
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        print_status "Opening port $SERVER_PORT for LAMControl server..."
        sudo ufw allow $SERVER_PORT/tcp
        
        # Enable ufw if not already enabled (with confirmation)
        if ! sudo ufw status | grep -q "Status: active"; then
            print_warning "Firewall is not active. Would you like to enable it? [y/N]"
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                sudo ufw --force enable
                print_success "Firewall enabled"
            else
                print_warning "Firewall not enabled. Make sure port $SERVER_PORT is accessible."
            fi
        fi
    else
        print_warning "ufw firewall not found. Make sure port $SERVER_PORT is accessible."
    fi
}

test_installation() {
    print_status "Testing installation..."
    
    # Test configuration
    cd "$INSTALL_DIR"
    if $PYTHON_CMD -c "import distributed_server; print('✅ Server module imports successfully')"; then
        print_success "Installation test passed"
    else
        print_error "Installation test failed"
        exit 1
    fi
}

create_admin_user() {
    print_status "Setting up admin user..."
    
    cd "$INSTALL_DIR"
    
    # Create admin credentials if they don't exist
    if [ ! -f "cache/admin_creds.json" ]; then
        mkdir -p cache
        $PYTHON_CMD -c "
import json
import secrets
import hashlib
from datetime import datetime, timezone

username = 'admin'
password = secrets.token_urlsafe(16)
password_hash = hashlib.sha256(password.encode()).hexdigest()

creds = {
    'username': username,
    'password': password,
    'password_hash': password_hash,
    'created_at': datetime.now(timezone.utc).isoformat()
}

with open('cache/admin_creds.json', 'w') as f:
    json.dump(creds, f, indent=2)

print(f'Admin credentials created:')
print(f'Username: {username}')
print(f'Password: {password}')
"
        print_success "Admin user created"
    else
        print_status "Admin user already exists"
    fi
}

show_completion_message() {
    print_success "LAMControl server installation completed!"
    echo
    print_status "Installation summary:"
    echo "  📁 Install directory: $INSTALL_DIR"
    echo "  🌐 Server address: http://$SERVER_HOST:$SERVER_PORT"
    echo "  🔧 Configuration: $INSTALL_DIR/config.json"
    echo "  🔐 Environment: $INSTALL_DIR/.env"
    echo "  📝 Service: $SERVICE_NAME"
    echo
    print_status "Server endpoints:"
    echo "  📊 Admin UI: http://your-server-ip:$SERVER_PORT/admin"
    echo "  🤖 R1 Client: http://your-server-ip:$SERVER_PORT/r1"
    echo "  🔌 API: http://your-server-ip:$SERVER_PORT/api"
    echo
    print_status "To start the server manually:"
    echo "  cd $INSTALL_DIR"
    echo "  ./start_server.sh"
    echo
    print_status "To install as system service:"
    echo "  sudo cp $INSTALL_DIR/${SERVICE_NAME}.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable $SERVICE_NAME"
    echo "  sudo systemctl start $SERVICE_NAME"
    echo
    print_status "To check service status:"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo "  journalctl -f -u $SERVICE_NAME"
    echo
    print_status "Admin credentials (save these!):"
    if [ -f "$INSTALL_DIR/cache/admin_creds.json" ]; then
        $PYTHON_CMD -c "
import json
with open('$INSTALL_DIR/cache/admin_creds.json') as f:
    creds = json.load(f)
print(f\"  Username: {creds['username']}\")
print(f\"  Password: {creds['password']}\")
"
    fi
    echo
    print_status "Next steps:"
    echo "  1. Start the server (manually or as service)"
    echo "  2. Access the admin UI to verify everything works"
    echo "  3. Install worker nodes using the worker installation script"
    echo "  4. Connect R1 client to start sending commands"
    echo
    print_warning "Security notes:"
    echo "  - Change the admin password after first login"
    echo "  - Keep your GROQ API key secure"
    echo "  - Consider using HTTPS in production"
    echo "  - Restrict access to admin UI if exposed to internet"
}

main() {
    parse_arguments "$@"
    
    print_status "LAMControl Server Installation"
    print_status "============================="
    echo
    
    check_requirements
    install_server
    create_configuration
    create_service_files
    setup_firewall
    test_installation
    create_admin_user
    show_completion_message
}

# Run main function with all arguments
main "$@"
