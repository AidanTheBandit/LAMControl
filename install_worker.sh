#!/bin/bash
"""
LAMControl Worker Node Installation Script

This script installs a LAMControl worker node with pluggable integrations
that connects to a central LAMControl server.
"""

set -e

# Default values
INTEGRATIONS=""
SERVER_HOST="localhost"
SERVER_PORT="8080"
WORKER_NAME=""
WORKER_LOCATION=""
WORKER_DESCRIPTION=""
WORKER_PORT="6000"
INSTALL_DIR="$HOME/lamcontrol-worker"
PYTHON_CMD="python3"
SERVICE_NAME="lamcontrol-worker"

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
LAMControl Worker Node Installation Script

This script installs a LAMControl worker node that connects to a LAMControl server
and provides pluggable integrations for task execution.

Usage: $0 [OPTIONS]

REQUIRED OPTIONS:
    --integrations LIST       Comma-separated list of integrations to install
    --server-host HOST        LAMControl server hostname/IP

OPTIONAL OPTIONS:
    --server-port PORT        Server port (default: 8080)
    --worker-name NAME        Worker name (default: auto-generated)
    --worker-location LOC     Worker location (default: hostname)
    --worker-description DESC Worker description
    --worker-port PORT        Worker port (default: 6000)
    --install-dir DIR         Installation directory (default: ~/lamcontrol-worker)
    --python-cmd CMD          Python command to use (default: python3)
    --service-name NAME       Systemd service name (default: lamcontrol-worker)
    --help                    Show this help message

AVAILABLE INTEGRATIONS:
    browser          - Web browser automation and search
      └─ Features: site_browsing, google_search, youtube_search, gmail, amazon
    
    computer         - Computer control and automation  
      └─ Features: volume_control, media_control, system_control, power_management
    
    messaging        - Messaging platform integrations
      └─ Features: discord, telegram, facebook
    
    ai               - AI and automation capabilities
      └─ Features: openinterpreter, automation

INTEGRATION SYNTAX:
    Basic: integration_name
    With features: integration_name:feature1,feature2,feature3
    
EXAMPLES:
    # Install worker with browser and computer integrations
    $0 --integrations browser,computer --server-host 192.168.1.100
    
    # Install worker with specific features
    $0 --integrations browser:google_search,youtube_search,computer:volume_control \\
       --server-host 192.168.1.100
    
    # Install named worker with custom settings
    $0 --integrations browser,computer,ai \\
       --server-host 192.168.1.100 \\
       --worker-name "Home-Assistant" \\
       --worker-location "Living Room" \\
       --worker-description "Home automation worker"

DEPLOYMENT SCENARIOS:
    🏠 Home Automation: browser,computer
    💼 Office Assistant: browser,computer,ai,messaging  
    🌐 Web Only: browser
    💻 System Control: computer
    🤖 AI Assistant: ai,messaging
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --integrations)
                INTEGRATIONS="$2"
                shift 2
                ;;
            --server-host)
                SERVER_HOST="$2"
                shift 2
                ;;
            --server-port)
                SERVER_PORT="$2"
                shift 2
                ;;
            --worker-name)
                WORKER_NAME="$2"
                shift 2
                ;;
            --worker-location)
                WORKER_LOCATION="$2"
                shift 2
                ;;
            --worker-description)
                WORKER_DESCRIPTION="$2"
                shift 2
                ;;
            --worker-port)
                WORKER_PORT="$2"
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

validate_arguments() {
    if [ -z "$INTEGRATIONS" ]; then
        print_error "No integrations specified. Use --integrations to specify integrations to install."
        echo
        print_status "Available integrations: browser, computer, messaging, ai"
        exit 1
    fi
    
    if [ -z "$SERVER_HOST" ]; then
        print_error "Server host not specified. Use --server-host to specify the LAMControl server."
        exit 1
    fi
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
    
    # Test server connectivity
    print_status "Testing server connectivity..."
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 5 "http://$SERVER_HOST:$SERVER_PORT/api/health" > /dev/null; then
            print_success "Server is reachable"
        else
            print_warning "Cannot reach server at http://$SERVER_HOST:$SERVER_PORT"
            print_warning "Worker will attempt to connect when started"
        fi
    else
        print_warning "curl not found - cannot test server connectivity"
    fi
    
    print_success "System requirements satisfied"
}

install_worker() {
    print_status "Installing LAMControl worker..."
    
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
    
    print_success "LAMControl worker installed"
}

install_integration_dependencies() {
    print_status "Installing integration-specific dependencies..."
    
    # Parse integrations and install dependencies
    IFS=',' read -ra INTEGRATION_ARRAY <<< "$INTEGRATIONS"
    
    for integration_spec in "${INTEGRATION_ARRAY[@]}"; do
        # Parse integration name (ignore features for dependency installation)
        IFS=':' read -ra SPEC_PARTS <<< "$integration_spec"
        INTEGRATION_NAME="${SPEC_PARTS[0]}"
        
        print_status "Installing dependencies for $INTEGRATION_NAME integration..."
        
        case $INTEGRATION_NAME in
            browser)
                print_status "Browser integration - no additional dependencies needed"
                ;;
            computer)
                print_status "Computer integration - no additional dependencies needed"
                ;;
            messaging)
                print_status "Installing messaging dependencies..."
                $PYTHON_CMD -m pip install --user playwright python-telegram-bot
                ;;
            ai)
                print_status "Installing AI dependencies..."
                $PYTHON_CMD -m pip install --user open-interpreter
                ;;
            *)
                print_warning "Unknown integration: $INTEGRATION_NAME"
                ;;
        esac
    done
    
    print_success "Integration dependencies installed"
}

create_configuration() {
    print_status "Creating worker configuration..."
    
    # Set defaults
    if [ -z "$WORKER_NAME" ]; then
        WORKER_NAME="LAMControl-Worker-$(hostname)-$(date +%s)"
    fi
    
    if [ -z "$WORKER_LOCATION" ]; then
        WORKER_LOCATION="$(hostname)"
    fi
    
    if [ -z "$WORKER_DESCRIPTION" ]; then
        WORKER_DESCRIPTION="LAMControl worker with integrations: $INTEGRATIONS"
    fi
    
    # Create worker configuration
    cat > worker_config.json << EOF
{
  "worker": {
    "name": "$WORKER_NAME",
    "location": "$WORKER_LOCATION", 
    "description": "$WORKER_DESCRIPTION",
    "port": $WORKER_PORT,
    "max_concurrent_tasks": 5
  },
  "server": {
    "endpoint": "http://$SERVER_HOST:$SERVER_PORT"
  },
  "integrations": {
EOF

    # Parse and configure integrations
    IFS=',' read -ra INTEGRATION_ARRAY <<< "$INTEGRATIONS"
    INTEGRATION_COUNT=${#INTEGRATION_ARRAY[@]}
    CURRENT_INDEX=0
    
    for integration_spec in "${INTEGRATION_ARRAY[@]}"; do
        CURRENT_INDEX=$((CURRENT_INDEX + 1))
        
        # Parse integration name and features
        IFS=':' read -ra SPEC_PARTS <<< "$integration_spec"
        INTEGRATION_NAME="${SPEC_PARTS[0]}"
        FEATURES="${SPEC_PARTS[1]:-}"
        
        # Add integration configuration
        cat >> worker_config.json << EOF
    "$INTEGRATION_NAME": {
      "enabled": true,
      "features": [
EOF
        
        if [ -n "$FEATURES" ]; then
            IFS=',' read -ra FEATURE_ARRAY <<< "$FEATURES"
            FEATURE_COUNT=${#FEATURE_ARRAY[@]}
            FEATURE_INDEX=0
            
            for feature in "${FEATURE_ARRAY[@]}"; do
                FEATURE_INDEX=$((FEATURE_INDEX + 1))
                if [ $FEATURE_INDEX -eq $FEATURE_COUNT ]; then
                    echo "        \"$feature\"" >> worker_config.json
                else
                    echo "        \"$feature\"," >> worker_config.json
                fi
            done
        fi
        
        cat >> worker_config.json << EOF
      ],
      "settings": {}
    }
EOF
        
        if [ $CURRENT_INDEX -lt $INTEGRATION_COUNT ]; then
            echo "," >> worker_config.json
        fi
    done
    
    cat >> worker_config.json << EOF
  }
}
EOF
    
    print_success "Configuration created: worker_config.json"
}

create_service_files() {
    print_status "Creating service files..."
    
    # Create startup script
    cat > start_worker.sh << EOF
#!/bin/bash
cd "$INSTALL_DIR"
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
$PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from integrated_worker_node import IntegratedWorkerNode, auto_discover_integrations
from integrations import IntegrationRegistry
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
with open('worker_config.json') as f:
    config = json.load(f)

worker_config = config['worker']
server_config = config['server']
integrations_config = config['integrations']

# Create worker
worker = IntegratedWorkerNode(
    server_endpoint=server_config['endpoint'],
    worker_port=worker_config['port'],
    worker_name=worker_config['name'],
    location=worker_config['location'],
    description=worker_config['description']
)

# Load integrations through auto-discovery
print('Loading integrations...')
worker.auto_discover_and_load_integrations(integrations_config)

print(f'Worker configured with {len(worker.capabilities)} capabilities:')
for cap in worker.capabilities:
    print(f'  - {cap}')

# Register with server
if worker.register_with_server():
    print('Successfully registered with server')
else:
    print('Failed to register with server - continuing anyway')

# Start heartbeat
worker.start_heartbeat()

# Start worker
print(f'Starting worker on port {worker_config[\"port\"]}...')
worker.app.run(host='0.0.0.0', port=worker_config['port'], debug=False)
"
EOF
    chmod +x start_worker.sh
    
    # Create systemd service file
    cat > ${SERVICE_NAME}.service << EOF
[Unit]
Description=LAMControl Worker Node
After=network.target
Wants=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(groups | cut -d' ' -f1)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/start_worker.sh
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

test_installation() {
    print_status "Testing installation..."
    
    cd "$INSTALL_DIR"
    
    # Test worker configuration
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
import json
from integrated_worker_node import IntegratedWorkerNode
from integrations import auto_discover_integrations

# Load and validate config
with open('worker_config.json') as f:
    config = json.load(f)

print('✅ Configuration loaded successfully')

# Test integration discovery
discovered = auto_discover_integrations()
print(f'✅ Discovered {len(discovered)} integrations')

# Test worker creation
worker = IntegratedWorkerNode(
    server_endpoint=config['server']['endpoint'],
    worker_port=config['worker']['port'],
    worker_name=config['worker']['name']
)
print('✅ Worker created successfully')

print('✅ Installation test passed')
"
    
    if [ $? -eq 0 ]; then
        print_success "Installation test passed"
    else
        print_error "Installation test failed"
        exit 1
    fi
}

show_completion_message() {
    print_success "LAMControl worker node installation completed!"
    echo
    print_status "Installation summary:"
    echo "  📁 Install directory: $INSTALL_DIR"
    echo "  🔧 Worker name: $WORKER_NAME"
    echo "  📍 Worker location: $WORKER_LOCATION"
    echo "  🌐 Server endpoint: http://$SERVER_HOST:$SERVER_PORT"
    echo "  🔌 Worker port: $WORKER_PORT"
    echo "  🧩 Integrations: $INTEGRATIONS"
    echo "  📝 Service: $SERVICE_NAME"
    echo
    print_status "To start the worker manually:"
    echo "  cd $INSTALL_DIR"
    echo "  ./start_worker.sh"
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
    print_status "Worker capabilities:"
    cd "$INSTALL_DIR"
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')
from integrations import auto_discover_integrations
import json

with open('worker_config.json') as f:
    config = json.load(f)

discovered = auto_discover_integrations()
for integration in discovered:
    if integration.name in config['integrations']:
        print(f'  📦 {integration.name}: {len(integration.get_capabilities())} capabilities')
        for cap in integration.get_capabilities():
            print(f'    • {cap}')
" 2>/dev/null || echo "  Use worker admin interface to view capabilities"
    echo
    print_status "Next steps:"
    echo "  1. Start the worker (manually or as service)"
    echo "  2. Verify worker appears in server admin UI"
    echo "  3. Test worker by sending commands through R1 client"
    echo "  4. Monitor worker logs for task execution"
    echo
    print_warning "Notes:"
    echo "  - Worker will automatically reconnect if server restarts"
    echo "  - Check firewall settings if worker cannot connect to server"
    echo "  - Worker capabilities depend on installed integrations"
    echo "  - Some integrations may require additional configuration"
}

main() {
    parse_arguments "$@"
    
    print_status "LAMControl Worker Node Installation"
    print_status "=================================="
    echo
    
    validate_arguments
    check_requirements
    install_worker
    install_integration_dependencies
    create_configuration
    create_service_files
    test_installation
    show_completion_message
}

# Run main function with all arguments
main "$@"
