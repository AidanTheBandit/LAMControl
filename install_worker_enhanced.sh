#!/bin/bash
"""
Enhanced LAMControl Worker Installation Script

This script installs a LAMControl worker with pluggable integrations
instead of fixed worker types.
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
CONFIG_FILE="worker_config.json"
PYTHON_CMD="python3"

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
LAMControl Enhanced Worker Installation Script

Usage: $0 [OPTIONS]

OPTIONS:
    --integrations INTEGRATIONS    Comma-separated list of integrations to install
                                  Format: integration_name:feature1,feature2
                                  Example: browser:site_browsing,google_search,computer:volume_control
    
    --server-host HOST            Server hostname/IP (default: localhost)
    --server-port PORT            Server port (default: 8080)
    --worker-name NAME            Worker name (default: auto-generated)
    --worker-location LOCATION    Worker location (default: hostname)
    --worker-description DESC     Worker description
    --worker-port PORT            Worker port (default: 6000)
    --install-dir DIR             Installation directory (default: ~/lamcontrol-worker)
    --config-file FILE            Configuration file name (default: worker_config.json)
    --python-cmd CMD              Python command to use (default: python3)
    --help                        Show this help message

AVAILABLE INTEGRATIONS:
    browser          - Web browser automation and search
      Features: site_browsing, google_search, youtube_search, gmail_integration, amazon_search
    
    computer         - Computer control and automation  
      Features: volume_control, media_control, system_control, power_management
    
    messaging        - Messaging platform integrations
      Features: discord, telegram, facebook
    
    ai               - AI and automation capabilities
      Features: openinterpreter, automation, llm_integration

EXAMPLES:
    # Install worker with browser and computer integrations
    $0 --integrations browser,computer --server-host 192.168.1.100
    
    # Install worker with specific features
    $0 --integrations browser:google_search,youtube_search,computer:volume_control
    
    # Install worker with custom settings
    $0 --integrations browser,computer,ai \\
       --worker-name "Home-Assistant" \\
       --worker-location "Living Room" \\
       --server-host 192.168.1.50
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
            --config-file)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --python-cmd)
                PYTHON_CMD="$2"
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
    
    # Parse integrations
    if [ -z "$INTEGRATIONS" ]; then
        print_error "No integrations specified. Use --integrations to specify integrations to install."
        exit 1
    fi
    
    # Create configuration file
    cat > "$CONFIG_FILE" << EOF
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
        cat >> "$CONFIG_FILE" << EOF
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
                    echo "        \"$feature\"" >> "$CONFIG_FILE"
                else
                    echo "        \"$feature\"," >> "$CONFIG_FILE"
                fi
            done
        fi
        
        cat >> "$CONFIG_FILE" << EOF
      ],
      "settings": {}
    }
EOF
        
        if [ $CURRENT_INDEX -lt $INTEGRATION_COUNT ]; then
            echo "," >> "$CONFIG_FILE"
        fi
    done
    
    cat >> "$CONFIG_FILE" << EOF
  }
}
EOF
    
    print_success "Configuration created: $CONFIG_FILE"
}

create_service_files() {
    print_status "Creating service files..."
    
    # Create startup script
    cat > start_worker.sh << EOF
#!/bin/bash
cd "$INSTALL_DIR"
$PYTHON_CMD enhanced_worker_launcher.py --config "$CONFIG_FILE" --verbose
EOF
    chmod +x start_worker.sh
    
    # Create systemd service file (optional)
    cat > lamcontrol-worker.service << EOF
[Unit]
Description=LAMControl Worker
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/start_worker.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Service files created"
    print_status "To install as systemd service:"
    print_status "  sudo cp lamcontrol-worker.service /etc/systemd/system/"
    print_status "  sudo systemctl enable lamcontrol-worker"
    print_status "  sudo systemctl start lamcontrol-worker"
}

install_integration_dependencies() {
    print_status "Installing integration-specific dependencies..."
    
    # Use the integration manager to install dependencies
    $PYTHON_CMD -c "
import sys
sys.path.append('.')
from integration_manager import EnhancedIntegrationManager
import json

# Load config
with open('$CONFIG_FILE') as f:
    config = json.load(f)

# Install dependencies for configured integrations
manager = EnhancedIntegrationManager()
for integration_name, int_config in config['integrations'].items():
    if int_config.get('enabled', True):
        features = int_config.get('features', [])
        if manager.install_dependencies(integration_name, features):
            print(f'✅ Dependencies installed for {integration_name}')
        else:
            print(f'❌ Failed to install dependencies for {integration_name}')
"
    
    print_success "Integration dependencies installed"
}

test_installation() {
    print_status "Testing installation..."
    
    # Test the configuration
    $PYTHON_CMD enhanced_worker_launcher.py --config "$CONFIG_FILE" --dry-run
    
    if [ $? -eq 0 ]; then
        print_success "Installation test passed"
    else
        print_error "Installation test failed"
        exit 1
    fi
}

show_completion_message() {
    print_success "LAMControl worker installation completed!"
    echo
    print_status "Installation summary:"
    echo "  📁 Install directory: $INSTALL_DIR"
    echo "  ⚙️  Configuration file: $CONFIG_FILE"
    echo "  🔧 Worker name: $WORKER_NAME"
    echo "  📍 Worker location: $WORKER_LOCATION"
    echo "  🌐 Server endpoint: http://$SERVER_HOST:$SERVER_PORT"
    echo "  🔌 Worker port: $WORKER_PORT"
    echo "  🧩 Integrations: $INTEGRATIONS"
    echo
    print_status "To start the worker:"
    echo "  cd $INSTALL_DIR"
    echo "  ./start_worker.sh"
    echo
    print_status "To start the worker in background:"
    echo "  cd $INSTALL_DIR"
    echo "  nohup ./start_worker.sh > worker.log 2>&1 &"
    echo
    print_status "To view worker logs:"
    echo "  tail -f $INSTALL_DIR/worker.log"
    echo
    print_status "To configure integrations:"
    echo "  Edit $INSTALL_DIR/$CONFIG_FILE"
    echo "  Restart the worker to apply changes"
}

main() {
    parse_arguments "$@"
    
    print_status "LAMControl Enhanced Worker Installation"
    print_status "======================================"
    
    check_requirements
    install_worker
    create_configuration
    install_integration_dependencies
    create_service_files
    test_installation
    show_completion_message
}

# Run main function with all arguments
main "$@"
