# LAMControl Distributed System Deployment Guide

## Overview

LAMControl Distributed System allows you to run a central server (in the cloud or on a local server) and connect multiple worker nodes from different computers. This enables scalable, distributed automation across multiple devices.

## Architecture

```
R1 Device ──► Central Server ──► Worker Nodes
                   │                 ├─ Browser Worker (PC 1)
                   │                 ├─ Computer Worker (PC 2)  
                   │                 ├─ Messaging Worker (PC 3)
                   └─ Dashboard      └─ AI Worker (PC 4)
```

## Quick Start

### 1. Server Setup (Cloud/VPS)

```bash
# Clone repository
git clone https://github.com/your-repo/LAMControl
cd LAMControl

# Install dependencies
pip install -r requirements.txt

# Configure for distributed server
cp config_distributed.json config.json
# Edit config.json: set "mode": "distributed_server"

# Start server
python main_distributed.py
```

Your server will be available at `http://your-server-ip:5000`

### 2. Worker Setup (Local Computers)

On each computer where you want to run workers:

```bash
# Clone repository (or copy files)
git clone https://github.com/your-repo/LAMControl
cd LAMControl

# Install dependencies
pip install -r requirements.txt

# Edit config_distributed.json:
# - Set "mode": "distributed_worker"
# - Set "worker.server_endpoint": "http://your-server-ip:5000"
# - Set "worker.type": "browser" (or "computer", "messaging", "ai")

# Start worker
python main_distributed.py
```

### 3. R1 Client Setup

```bash
# Use the enhanced distributed client
python r1_client_distributed.py --servers http://your-server-ip:5000 "your command"
```

## Detailed Setup Instructions

### Server Deployment

#### Option 1: Cloud VPS (Recommended)

1. **Choose a VPS provider** (DigitalOcean, Linode, AWS EC2, etc.)
2. **Create Ubuntu 20.04+ server** with at least 1GB RAM
3. **Install Python and dependencies:**

```bash
sudo apt update
sudo apt install python3 python3-pip git
git clone https://github.com/your-repo/LAMControl
cd LAMControl
pip3 install -r requirements.txt
```

4. **Configure server:**

```bash
cp config_distributed.json config.json
nano config.json
```

Edit the configuration:
```json
{
  "mode": "distributed_server",
  "distributed": {
    "server_host": "0.0.0.0",
    "server_port": 5000
  },
  "groq_model": "llama-3.3-70b-versatile"
}
```

5. **Set up GROQ API key:**

```bash
nano .env
```

Add your GROQ API key:
```
GROQ_API_KEY=your_groq_api_key_here
```

6. **Start server with systemd (optional):**

```bash
sudo nano /etc/systemd/system/lamcontrol.service
```

```ini
[Unit]
Description=LAMControl Distributed Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/LAMControl
ExecStart=/usr/bin/python3 main_distributed.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable lamcontrol
sudo systemctl start lamcontrol
```

7. **Configure firewall:**

```bash
sudo ufw allow 5000
sudo ufw enable
```

#### Option 2: Local Server

If running the server on your local network:

1. **Choose a dedicated computer** (can be a Raspberry Pi, old laptop, etc.)
2. **Follow same installation steps as VPS**
3. **Configure router port forwarding** if you want external access
4. **Use local IP address** for worker connections

### Worker Node Deployment

#### Browser Worker (Web Automation)

Best deployed on: **Windows/Mac desktop with Chrome/Firefox**

```bash
# Install browser dependencies
playwright install

# Configure worker
cp config_distributed.json config.json
```

Edit config.json:
```json
{
  "mode": "distributed_worker",
  "worker": {
    "type": "browser",
    "server_endpoint": "http://your-server-ip:5000",
    "worker_port": 6001
  }
}
```

Start worker:
```bash
python main_distributed.py
# OR use the convenience script:
python workers/browser_worker.py http://your-server-ip:5000
```

#### Computer Control Worker (System Control)

Best deployed on: **Your main desktop/laptop**

```bash
# Configure worker
cp config_distributed.json config.json
```

Edit config.json:
```json
{
  "mode": "distributed_worker",
  "worker": {
    "type": "computer",
    "server_endpoint": "http://your-server-ip:5000",
    "worker_port": 6002
  }
}
```

Start worker:
```bash
python main_distributed.py
# OR:
python workers/computer_worker.py http://your-server-ip:5000
```

#### Messaging Worker (Social Media)

Best deployed on: **Computer with browser profiles/sessions**

1. **Set up browser sessions** for your social accounts
2. **Configure worker** as above with `"type": "messaging"`
3. **Start worker**

#### AI Worker (OpenInterpreter)

Best deployed on: **Powerful computer with GPU (optional)**

1. **Install OpenInterpreter:**
```bash
pip install open-interpreter
```

2. **Configure API keys** in config
3. **Start worker** with `"type": "ai"`

### Multiple Workers on One Computer

You can run multiple worker types on the same computer:

```bash
# Start all workers using the convenience script
./start_all_workers.sh http://your-server-ip:5000

# Or start individual workers on different ports
python workers/browser_worker.py http://your-server-ip:5000 6001 &
python workers/computer_worker.py http://your-server-ip:5000 6002 &
python workers/messaging_worker.py http://your-server-ip:5000 6003 &
python workers/ai_worker.py http://your-server-ip:5000 6004 &
```

## Configuration Examples

### Minimal Server Config
```json
{
  "mode": "distributed_server",
  "distributed": {
    "server_host": "0.0.0.0",
    "server_port": 5000
  },
  "groq_model": "llama-3.3-70b-versatile",
  "debug": false
}
```

### Production Server Config
```json
{
  "mode": "distributed_server",
  "distributed": {
    "server_host": "0.0.0.0",
    "server_port": 5000,
    "max_workers_per_type": 10,
    "task_timeout": 300,
    "worker_heartbeat_interval": 30,
    "worker_offline_timeout": 120
  },
  "groq_model": "llama-3.3-70b-versatile",
  "debug": false
}
```

### Worker Config Template
```json
{
  "mode": "distributed_worker",
  "worker": {
    "type": "browser",
    "server_endpoint": "http://your-server:5000",
    "worker_port": 6001,
    "max_concurrent_tasks": 5,
    "auto_register": true
  }
}
```

## Usage Examples

### R1 Commands

```bash
# Using original client
python r1_client.py "open youtube music and play weezer"

# Using distributed client
python r1_client_distributed.py "open youtube music and play weezer"

# Using multiple servers
python r1_client_distributed.py --servers http://server1:5000,http://server2:5000 "turn volume to 50"

# Check server status
python r1_client_distributed.py --status

# Monitor servers
python r1_client_distributed.py --monitor
```

### Admin Dashboard

Access the admin dashboard at: `http://your-server-ip:5000`

Features:
- View registered workers
- Monitor system health
- Send test prompts
- View task history
- Real-time worker status

## Troubleshooting

### Common Issues

1. **Worker can't connect to server**
   - Check firewall settings
   - Verify server IP and port
   - Ensure server is running

2. **Tasks not executing**
   - Check worker logs
   - Verify worker capabilities
   - Ensure proper authentication

3. **Server performance issues**
   - Monitor resource usage
   - Scale workers horizontally
   - Optimize task distribution

### Logs and Monitoring

```bash
# Server logs
tail -f logs/server.log

# Worker logs (when using convenience scripts)
tail -f logs/browser_worker.log
tail -f logs/computer_worker.log

# Check worker status
curl http://your-server:5000/api/workers
```

## Security Considerations

1. **Use HTTPS in production** (add reverse proxy with SSL)
2. **Secure API keys** (use environment variables)
3. **Firewall configuration** (restrict access to necessary ports)
4. **Worker authentication** (API keys are auto-generated)
5. **Network isolation** (use VPN for worker connections if needed)

## Scaling

### Horizontal Scaling

- Add more worker nodes for increased capacity
- Run multiple workers of the same type for redundancy
- Deploy workers across different geographic locations

### Vertical Scaling

- Increase server resources (CPU, RAM)
- Use more powerful worker machines
- Optimize task distribution algorithms

## Next Steps

1. **Set up monitoring** (Prometheus, Grafana)
2. **Implement load balancing** (nginx, HAProxy)
3. **Add SSL/TLS** (Let's Encrypt, Cloudflare)
4. **Create Docker containers** for easier deployment
5. **Set up CI/CD** for automated deployments
