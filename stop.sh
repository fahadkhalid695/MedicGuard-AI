#!/bin/bash
# ============================================================
# MediGuard AI — Stop All Services
# ============================================================

PROJECT_DIR="/home/ubuntu/MedicGuard-AI"
LOG_DIR="$PROJECT_DIR/logs"

echo "Stopping MediGuard AI services..."

# Kill by PID files
for PIDFILE in "$LOG_DIR"/*.pid; do
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            echo "  Stopped $(basename $PIDFILE .pid) (PID: $PID)"
        fi
        rm -f "$PIDFILE"
    fi
done

# Kill by port (fallback)
for PORT in 8000 8001 8765 3000 3001; do
    PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
    fi
done

# Kill any remaining python processes
pkill -f "python -m agents" 2>/dev/null || true
pkill -f "python -m dispatcher" 2>/dev/null || true
pkill -f "mock_generator" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true

echo "All services stopped."
