#!/bin/bash
# ============================================================
# MediGuard AI — Complete Startup & Health Check Script
# ============================================================
# Usage: chmod +x start.sh && ./start.sh
# ============================================================

set -e

PROJECT_DIR="/home/ubuntu/MedicGuard-AI"
VENV="$PROJECT_DIR/.venv/bin"
LOG_DIR="$PROJECT_DIR/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_ok() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_fail() {
    echo -e "  ${RED}✗${NC} $1"
}

print_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

# Create log directory
mkdir -p "$LOG_DIR"

# ============================================================
print_header "Step 1: Checking Prerequisites"
# ============================================================

# Check Python
if command -v python3 &> /dev/null; then
    print_ok "Python3: $(python3 --version)"
else
    print_fail "Python3 not found"
    exit 1
fi

# Check Node
if command -v node &> /dev/null; then
    print_ok "Node.js: $(node --version)"
else
    print_fail "Node.js not found"
    exit 1
fi

# Check PostgreSQL
if pg_isready -h localhost -q 2>/dev/null; then
    print_ok "PostgreSQL: running"
else
    print_fail "PostgreSQL not running. Starting..."
    sudo systemctl start postgresql
    sleep 2
    if pg_isready -h localhost -q 2>/dev/null; then
        print_ok "PostgreSQL: started"
    else
        print_fail "Cannot start PostgreSQL"
        exit 1
    fi
fi

# Check Redis
if redis-cli ping 2>/dev/null | grep -q PONG; then
    print_ok "Redis: running"
else
    print_fail "Redis not running. Starting..."
    sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null
    sleep 1
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        print_ok "Redis: started"
    else
        print_fail "Cannot start Redis"
        exit 1
    fi
fi

# Check venv
if [ -f "$VENV/activate" ]; then
    print_ok "Python venv: found"
else
    print_warn "Python venv not found. Creating..."
    python3 -m venv "$PROJECT_DIR/.venv"
    source "$VENV/activate"
    pip install -q -r "$PROJECT_DIR/vitals-service/requirements.txt"
    pip install -q -r "$PROJECT_DIR/agents/requirements.txt"
    pip install -q -r "$PROJECT_DIR/dispatcher/requirements.txt"
    pip install -q -r "$PROJECT_DIR/patient-api/requirements.txt"
    print_ok "Python venv: created and dependencies installed"
fi

# Check node_modules
if [ -d "$PROJECT_DIR/doctor-dashboard/node_modules" ]; then
    print_ok "Dashboard node_modules: found"
else
    print_warn "Installing dashboard dependencies..."
    cd "$PROJECT_DIR/doctor-dashboard" && npm install --silent
    print_ok "Dashboard dependencies installed"
fi

# ============================================================
print_header "Step 2: Database Check"
# ============================================================

# Check if patients table has data
PATIENT_COUNT=$(PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -t -c "SELECT COUNT(*) FROM patients;" 2>/dev/null | tr -d ' ')

if [ "$PATIENT_COUNT" -gt 0 ] 2>/dev/null; then
    print_ok "Patients table: $PATIENT_COUNT patients found"
else
    print_warn "No patients found. Running seed..."
    PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f "$PROJECT_DIR/migrations/001_seed_patients.sql" 2>/dev/null
    print_ok "Seed data inserted"
fi

# ============================================================
print_header "Step 3: Killing Previous Instances"
# ============================================================

# Kill any existing services on our ports
for PORT in 8000 8001 8765 3000 3001; do
    PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        print_warn "Killed process on port $PORT (PID: $PID)"
    fi
done

# Kill any leftover python agent/dispatcher processes
pkill -f "python -m agents" 2>/dev/null || true
pkill -f "python -m dispatcher" 2>/dev/null || true
pkill -f "mock_generator" 2>/dev/null || true

sleep 2
print_ok "Previous instances cleared"

# ============================================================
print_header "Step 4: Starting Services"
# ============================================================

cd "$PROJECT_DIR"
source "$VENV/activate"

# 1. Vitals Ingestion Service (port 8000)
cd "$PROJECT_DIR/vitals-service"
nohup "$VENV/uvicorn" app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/vitals-service.log" 2>&1 &
echo $! > "$LOG_DIR/vitals-service.pid"
print_ok "Vitals Service starting (port 8000)..."

# 2. Alert Dispatcher + WebSocket (port 8765)
cd "$PROJECT_DIR"
nohup "$VENV/python" -m dispatcher > "$LOG_DIR/dispatcher.log" 2>&1 &
echo $! > "$LOG_DIR/dispatcher.pid"
print_ok "Alert Dispatcher starting (port 8765)..."

# 3. Patient API (port 8001)
cd "$PROJECT_DIR/patient-api"
nohup "$VENV/uvicorn" app.main:app --host 0.0.0.0 --port 8001 > "$LOG_DIR/patient-api.log" 2>&1 &
echo $! > "$LOG_DIR/patient-api.pid"
print_ok "Patient API starting (port 8001)..."

# 4. Doctor Dashboard (port 3000)
cd "$PROJECT_DIR/doctor-dashboard"
nohup npx vite --host 0.0.0.0 --port 3000 > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$LOG_DIR/dashboard.pid"
print_ok "Doctor Dashboard starting (port 3000)..."

# 5. Wait for services to be ready
sleep 5

# ============================================================
print_header "Step 5: Health Checks"
# ============================================================

# Check Vitals Service
if curl -s http://localhost:8000/api/health | grep -q "ok"; then
    print_ok "Vitals Service: healthy (http://localhost:8000)"
else
    print_fail "Vitals Service: not responding"
    echo "    Check logs: tail -f $LOG_DIR/vitals-service.log"
fi

# Check Patient API
if curl -s http://localhost:8001/api/health | grep -q "ok"; then
    print_ok "Patient API: healthy (http://localhost:8001)"
else
    print_fail "Patient API: not responding"
    echo "    Check logs: tail -f $LOG_DIR/patient-api.log"
fi

# Check WebSocket port
if lsof -i :8765 > /dev/null 2>&1; then
    print_ok "WebSocket (Dispatcher): listening on port 8765"
else
    print_fail "WebSocket (Dispatcher): not listening"
    echo "    Check logs: tail -f $LOG_DIR/dispatcher.log"
fi

# Check Dashboard
if curl -s http://localhost:3000 | grep -q "MediGuard"; then
    print_ok "Doctor Dashboard: serving (http://localhost:3000)"
else
    # Give it more time (Vite can be slow to start)
    sleep 5
    if curl -s http://localhost:3000 | grep -q "MediGuard"; then
        print_ok "Doctor Dashboard: serving (http://localhost:3000)"
    else
        print_fail "Doctor Dashboard: not responding"
        echo "    Check logs: tail -f $LOG_DIR/dashboard.log"
    fi
fi

# ============================================================
print_header "Step 6: Starting Mock Data Generator"
# ============================================================

cd "$PROJECT_DIR/vitals-service"
nohup "$VENV/python" mock_generator.py > "$LOG_DIR/mock-generator.log" 2>&1 &
echo $! > "$LOG_DIR/mock-generator.pid"

sleep 3

# Check if mock generator is sending data successfully
if grep -q "Sent: 10/10\|Sent: 9/10\|Sent: 8/10" "$LOG_DIR/mock-generator.log" 2>/dev/null; then
    print_ok "Mock Generator: sending vitals data"
else
    if grep -q "Error" "$LOG_DIR/mock-generator.log" 2>/dev/null; then
        print_fail "Mock Generator: errors detected"
        echo "    Check logs: tail -f $LOG_DIR/mock-generator.log"
    else
        print_warn "Mock Generator: started (checking...)"
    fi
fi

# ============================================================
print_header "Step 7: Testing Data Flow"
# ============================================================

# Send a test vital reading directly
TEST_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/vitals \
    -H "Content-Type: application/json" \
    -d '{
        "patient_id": "00000000-0000-0000-0000-000000000001",
        "heart_rate": 75,
        "bp_systolic": 120,
        "bp_diastolic": 80,
        "spo2": 98.0,
        "temperature": 36.8,
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
    }')

if [ "$TEST_RESPONSE" = "201" ]; then
    print_ok "Data flow test: vitals accepted (HTTP 201)"
else
    print_fail "Data flow test: HTTP $TEST_RESPONSE"
fi

# Check Redis cache
CACHED=$(redis-cli HGET "vitals:latest:00000000-0000-0000-0000-000000000001" heart_rate 2>/dev/null)
if [ -n "$CACHED" ]; then
    print_ok "Redis cache: working (HR=$CACHED)"
else
    print_warn "Redis cache: no data yet (may take a moment)"
fi

# ============================================================
print_header "Summary"
# ============================================================

EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "YOUR_EC2_IP")

echo ""
echo -e "  ${GREEN}All services started!${NC}"
echo ""
echo "  Access the dashboard at:"
echo -e "  ${BLUE}http://$EC2_IP:3000${NC}"
echo ""
echo "  API documentation:"
echo -e "  ${BLUE}http://$EC2_IP:8000/docs${NC}  (Vitals API)"
echo -e "  ${BLUE}http://$EC2_IP:8001/docs${NC}  (Patient API)"
echo ""
echo "  Logs directory: $LOG_DIR/"
echo "  View logs:  tail -f $LOG_DIR/vitals-service.log"
echo ""
echo "  Stop all:   $PROJECT_DIR/stop.sh"
echo ""
