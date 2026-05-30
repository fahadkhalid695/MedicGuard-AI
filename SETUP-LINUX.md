# MediGuard AI — Complete Setup Guide (Linux / Ubuntu)

This guide covers Ubuntu 22.04+ / Debian-based distros. Adapt package manager commands for Fedora/Arch.

---

## Prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential
```

---

## Step 1: Install Python 3.11+

```bash
sudo apt install -y python3 python3-pip python3-venv

# Verify
python3 --version   # Should be 3.11+
pip3 --version
```

If your distro ships an older Python:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
# Use python3.12 and pip3.12 in all commands below
```

---

## Step 2: Install Node.js 18+

```bash
# Using NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version   # v20.x
npm --version
```

---

## Step 3: Install PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib

# Start and enable
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify
sudo -u postgres psql -c "SELECT version();"
```

---

## Step 4: Install Redis

```bash
sudo apt install -y redis-server

# Start and enable
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Should return: PONG
```

---

## Step 5: Clone the Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/MediGuard-AI.git
cd MediGuard-AI
```

---

## Step 6: Create the Database

```bash
# Switch to postgres user and create DB + user
sudo -u postgres psql <<EOF
CREATE DATABASE mediguard;
CREATE USER mediguard WITH PASSWORD 'mediguard123';
GRANT ALL PRIVILEGES ON DATABASE mediguard TO mediguard;
\c mediguard
GRANT ALL ON SCHEMA public TO mediguard;
EOF

# Run schema and migrations
PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f schema.sql
PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f migrations/002_feedback_loop.sql
PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f migrations/003_alert_dispatches.sql
PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f migrations/004_patient_responses.sql
PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f migrations/005_consultations_and_notes.sql
PGPASSWORD=mediguard123 psql -U mediguard -h localhost -d mediguard -f migrations/006_agent_actions.sql
```

---

## Step 7: Create Python Virtual Environment

```bash
# Create a shared venv for all Python services
python3 -m venv .venv
source .venv/bin/activate

# Install all Python dependencies
pip install -r vitals-service/requirements.txt
pip install -r agents/requirements.txt
pip install -r dispatcher/requirements.txt
pip install -r patient-api/requirements.txt
```

---

## Step 8: Install Node.js Dependencies

```bash
cd backend && npm install && cd ..
cd doctor-dashboard && npm install && cd ..
cd dashboard && npm install && cd ..
```

---

## Step 9: Configure Environment Files

```bash
# Copy all .env.example files
cp vitals-service/.env.example vitals-service/.env
cp agents/.env.example agents/.env
cp dispatcher/.env.example dispatcher/.env
cp patient-api/.env.example patient-api/.env
```

Now edit each `.env` file:

### vitals-service/.env
```bash
cat > vitals-service/.env << 'EOF'
DATABASE_URL=postgresql://mediguard:mediguard123@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
VITALS_CACHE_TTL=60
EOF
```

### agents/.env
```bash
cat > agents/.env << 'EOF'
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATABASE_URL=postgresql://mediguard:mediguard123@localhost:5432/mediguard
LLM_MODEL=claude-sonnet-4-20250514
PATIENT_IDS=
ORCHESTRATOR_WINDOW_SEC=5
ORCHESTRATOR_DEDUP_SEC=30
AUTONOMOUS_ACTIONS_ENABLED=true
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
EOF
```

### dispatcher/.env
```bash
cat > dispatcher/.env << 'EOF'
DATABASE_URL=postgresql://mediguard:mediguard123@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=alerts@mediguard.ai
HOSPITAL_NOTIFY_URL=http://localhost:8000/api/hospital-notify
DASHBOARD_BASE_URL=http://localhost:3000
WS_HOST=0.0.0.0
WS_PORT=8765
EOF
```

### patient-api/.env
```bash
cat > patient-api/.env << 'EOF'
DATABASE_URL=postgresql://mediguard:mediguard123@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-your-key-here
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
DASHBOARD_BASE_URL=http://localhost:3000
PORT=8001
EOF
```

> **Important:** Replace `sk-ant-your-key-here` with your actual Anthropic API key from https://console.anthropic.com/

---

## Step 10: Run the Application

Open **7 terminal tabs/windows** (or use `tmux`/`screen`):

### Option A: Manual (7 terminals)

```bash
# Terminal 1: Vitals Ingestion Service
cd ~/MediGuard-AI
source .venv/bin/activate
uvicorn vitals-service.app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir .
# OR:
cd vitals-service && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Terminal 2: Multi-Agent System
cd ~/MediGuard-AI
source .venv/bin/activate
python -m agents
```

```bash
# Terminal 3: Alert Dispatcher
cd ~/MediGuard-AI
source .venv/bin/activate
python -m dispatcher
```

```bash
# Terminal 4: Patient API
cd ~/MediGuard-AI/patient-api
source ../.venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

```bash
# Terminal 5: Feedback Backend
cd ~/MediGuard-AI/backend
npm run dev
```

```bash
# Terminal 6: Doctor Dashboard
cd ~/MediGuard-AI/doctor-dashboard
npm run dev
```

```bash
# Terminal 7: Mock Data Generator
cd ~/MediGuard-AI/vitals-service
source ../.venv/bin/activate
python mock_generator.py
```

---

### Option B: Using tmux (single terminal)

```bash
sudo apt install -y tmux

# Create a tmux session
tmux new-session -d -s mediguard

# Activate venv in each pane
ACTIVATE="source ~/MediGuard-AI/.venv/bin/activate && cd ~/MediGuard-AI"

# Pane 0: Vitals Service
tmux send-keys -t mediguard "$ACTIVATE && cd vitals-service && uvicorn app.main:app --host 0.0.0.0 --port 8000" Enter

# Pane 1: Agents
tmux split-window -h -t mediguard
tmux send-keys -t mediguard "$ACTIVATE && python -m agents" Enter

# Pane 2: Dispatcher
tmux split-window -v -t mediguard
tmux send-keys -t mediguard "$ACTIVATE && python -m dispatcher" Enter

# Pane 3: Patient API
tmux select-pane -t 0
tmux split-window -v -t mediguard
tmux send-keys -t mediguard "$ACTIVATE && cd patient-api && uvicorn app.main:app --host 0.0.0.0 --port 8001" Enter

# New window for Node services
tmux new-window -t mediguard -n "node"
tmux send-keys -t mediguard "cd ~/MediGuard-AI/backend && npm run dev" Enter

tmux split-window -h -t mediguard
tmux send-keys -t mediguard "cd ~/MediGuard-AI/doctor-dashboard && npm run dev" Enter

# New window for mock generator
tmux new-window -t mediguard -n "mock"
tmux send-keys -t mediguard "$ACTIVATE && cd vitals-service && python mock_generator.py" Enter

# Attach to session
tmux attach -t mediguard
```

---

### Option C: Using a process manager (systemd)

Create a service file for each component. Example for the vitals service:

```bash
sudo tee /etc/systemd/system/mediguard-vitals.service << 'EOF'
[Unit]
Description=MediGuard AI Vitals Service
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/MediGuard-AI/vitals-service
Environment="PATH=/home/your-username/MediGuard-AI/.venv/bin:/usr/bin"
ExecStart=/home/your-username/MediGuard-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mediguard-vitals
sudo systemctl start mediguard-vitals
```

Repeat for each service (agents, dispatcher, patient-api, backend).

---

## Step 11: Verify Everything is Running

```bash
# Check services
curl -s http://localhost:8000/api/health | python3 -m json.tool
curl -s http://localhost:8001/api/health | python3 -m json.tool
curl -s http://localhost:3001/api/health | python3 -m json.tool

# Check infrastructure
sudo systemctl status postgresql
sudo systemctl status redis-server
redis-cli ping
```

---

## Step 12: Access the Dashboards

| Service | URL |
|---------|-----|
| Doctor Dashboard | http://localhost:3000 |
| Vitals API (Swagger) | http://localhost:8000/docs |
| Patient API (Swagger) | http://localhost:8001/docs |
| Feedback Backend | http://localhost:3001 |

---

## Firewall Configuration (if needed)

```bash
# Allow the service ports
sudo ufw allow 8000/tcp   # Vitals API
sudo ufw allow 8001/tcp   # Patient API
sudo ufw allow 3000/tcp   # Doctor Dashboard
sudo ufw allow 3001/tcp   # Feedback Backend
sudo ufw allow 8765/tcp   # WebSocket
```

---

## Running as a Background Service (Production)

For production deployments, use a process manager:

```bash
# Install PM2 for Node services
sudo npm install -g pm2

# Start Node services
cd ~/MediGuard-AI/backend
pm2 start "npm run dev" --name mediguard-backend

cd ~/MediGuard-AI/doctor-dashboard
pm2 start "npm run dev" --name mediguard-dashboard

# Save PM2 config
pm2 save
pm2 startup  # generates systemd service for PM2
```

For Python services, use `supervisord`:

```bash
sudo apt install -y supervisor

sudo tee /etc/supervisor/conf.d/mediguard.conf << 'EOF'
[program:mediguard-vitals]
command=/home/your-username/MediGuard-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/home/your-username/MediGuard-AI/vitals-service
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/mediguard/vitals.err.log
stdout_logfile=/var/log/mediguard/vitals.out.log

[program:mediguard-agents]
command=/home/your-username/MediGuard-AI/.venv/bin/python -m agents
directory=/home/your-username/MediGuard-AI
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/mediguard/agents.err.log
stdout_logfile=/var/log/mediguard/agents.out.log

[program:mediguard-dispatcher]
command=/home/your-username/MediGuard-AI/.venv/bin/python -m dispatcher
directory=/home/your-username/MediGuard-AI
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/mediguard/dispatcher.err.log
stdout_logfile=/var/log/mediguard/dispatcher.out.log

[program:mediguard-patient-api]
command=/home/your-username/MediGuard-AI/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
directory=/home/your-username/MediGuard-AI/patient-api
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/mediguard/patient-api.err.log
stdout_logfile=/var/log/mediguard/patient-api.out.log
EOF

sudo mkdir -p /var/log/mediguard
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
```

---

## Troubleshooting

### PostgreSQL: "peer authentication failed"

Edit `pg_hba.conf` to allow password auth:
```bash
sudo nano /etc/postgresql/15/main/pg_hba.conf
```
Change the line:
```
local   all   all   peer
```
to:
```
local   all   all   md5
```
Then restart:
```bash
sudo systemctl restart postgresql
```

### Redis: "Connection refused"

```bash
sudo systemctl status redis-server
# If not running:
sudo systemctl start redis-server
```

### Python: "ModuleNotFoundError"

Make sure you activated the venv:
```bash
source ~/MediGuard-AI/.venv/bin/activate
which python  # Should point to .venv/bin/python
```

### Port already in use

```bash
# Find what's using the port
sudo lsof -i :8000
# Kill it
sudo kill -9 <PID>
```

### Permission denied on .env files

```bash
chmod 600 vitals-service/.env agents/.env dispatcher/.env patient-api/.env
```

### psql: "could not connect to server"

Check if PostgreSQL is listening on localhost:
```bash
sudo ss -tlnp | grep 5432
```
If empty, check the config:
```bash
sudo nano /etc/postgresql/15/main/postgresql.conf
# Ensure: listen_addresses = 'localhost'
sudo systemctl restart postgresql
```

---

## Quick Start Script

Save this as `start-all.sh` in the project root:

```bash
#!/bin/bash
# MediGuard AI - Start All Services

set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_DIR/.venv/bin"

echo "=========================================="
echo "  MediGuard AI - Starting All Services"
echo "=========================================="

# Check prerequisites
echo "Checking prerequisites..."
redis-cli ping > /dev/null 2>&1 || { echo "ERROR: Redis not running"; exit 1; }
pg_isready > /dev/null 2>&1 || { echo "ERROR: PostgreSQL not running"; exit 1; }
echo "✓ Redis and PostgreSQL are running"

# Start Python services in background
echo "Starting Python services..."
$VENV/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
PIDS+=($!)
echo "  ✓ Vitals Service (port 8000)"

cd "$PROJECT_DIR"
$VENV/python -m agents &
PIDS+=($!)
echo "  ✓ Agent System"

$VENV/python -m dispatcher &
PIDS+=($!)
echo "  ✓ Alert Dispatcher"

cd "$PROJECT_DIR/patient-api"
$VENV/uvicorn app.main:app --host 0.0.0.0 --port 8001 &
PIDS+=($!)
echo "  ✓ Patient API (port 8001)"

# Start Node services
echo "Starting Node services..."
cd "$PROJECT_DIR/backend"
npm run dev &
PIDS+=($!)
echo "  ✓ Feedback Backend (port 3001)"

cd "$PROJECT_DIR/doctor-dashboard"
npm run dev &
PIDS+=($!)
echo "  ✓ Doctor Dashboard (port 3000)"

echo ""
echo "=========================================="
echo "  All services started!"
echo "  Dashboard: http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all services"

# Trap Ctrl+C to kill all background processes
trap 'echo "Stopping..."; kill ${PIDS[@]} 2>/dev/null; exit 0' INT TERM

# Wait for all
wait
```

Make it executable:
```bash
chmod +x start-all.sh
./start-all.sh
```

---

## Docker Alternative (Optional)

If you prefer containers, create a `docker-compose.yml`:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in

# Install Docker Compose
sudo apt install -y docker-compose-plugin
```

A full Docker setup would require Dockerfiles for each service — that's a separate enhancement if needed.
