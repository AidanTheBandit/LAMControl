#!/bin/bash
"""
Stop All Workers Script for LAMControl Distributed System

This script stops all running worker processes.
"""

echo "Stopping all LAMControl Workers..."
echo "================================="

# Check if PID file exists
if [ ! -f logs/worker_pids.txt ]; then
    echo "No worker PID file found. Workers may not be running."
    exit 1
fi

# Read PIDs and kill processes
while read pid; do
    if [ -n "$pid" ]; then
        if kill -0 $pid 2>/dev/null; then
            echo "Stopping worker with PID: $pid"
            kill $pid
        else
            echo "Worker with PID $pid is not running"
        fi
    fi
done < logs/worker_pids.txt

# Wait a moment for graceful shutdown
sleep 2

# Force kill any remaining processes
while read pid; do
    if [ -n "$pid" ]; then
        if kill -0 $pid 2>/dev/null; then
            echo "Force killing worker with PID: $pid"
            kill -9 $pid
        fi
    fi
done < logs/worker_pids.txt

# Clean up PID file
rm -f logs/worker_pids.txt

echo "All workers stopped."
