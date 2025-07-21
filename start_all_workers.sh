#!/bin/bash
"""
Start All Workers Script for LAMControl Distributed System

This script starts all worker types on a local machine.
Workers will connect to the specified LAMControl server.

Usage:
    ./start_all_workers.sh <server_endpoint>
    
Example:
    ./start_all_workers.sh http://your-server.com:5000
"""

# Check if server endpoint is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <server_endpoint>"
    echo "Example: $0 http://localhost:5000"
    exit 1
fi

SERVER_ENDPOINT=$1

echo "Starting LAMControl Workers for server: $SERVER_ENDPOINT"
echo "=========================================="

# Create logs directory
mkdir -p logs

# Start Browser Worker (port 6001)
echo "Starting Browser Worker on port 6001..."
python3 workers/browser_worker.py $SERVER_ENDPOINT 6001 > logs/browser_worker.log 2>&1 &
BROWSER_PID=$!
echo "Browser Worker PID: $BROWSER_PID"

# Start Computer Worker (port 6002)
echo "Starting Computer Control Worker on port 6002..."
python3 workers/computer_worker.py $SERVER_ENDPOINT 6002 > logs/computer_worker.log 2>&1 &
COMPUTER_PID=$!
echo "Computer Control Worker PID: $COMPUTER_PID"

# Start Messaging Worker (port 6003)
echo "Starting Messaging Worker on port 6003..."
python3 workers/messaging_worker.py $SERVER_ENDPOINT 6003 > logs/messaging_worker.log 2>&1 &
MESSAGING_PID=$!
echo "Messaging Worker PID: $MESSAGING_PID"

# Start AI Worker (port 6004)
echo "Starting AI Worker on port 6004..."
python3 workers/ai_worker.py $SERVER_ENDPOINT 6004 > logs/ai_worker.log 2>&1 &
AI_PID=$!
echo "AI Worker PID: $AI_PID"

# Save PIDs to file for later cleanup
echo "$BROWSER_PID" > logs/worker_pids.txt
echo "$COMPUTER_PID" >> logs/worker_pids.txt
echo "$MESSAGING_PID" >> logs/worker_pids.txt
echo "$AI_PID" >> logs/worker_pids.txt

echo ""
echo "All workers started! PIDs saved to logs/worker_pids.txt"
echo "Logs are being written to logs/ directory"
echo ""
echo "To stop all workers, run: ./stop_all_workers.sh"
echo "To view worker status: tail -f logs/*.log"
