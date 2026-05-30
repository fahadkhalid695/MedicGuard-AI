# MediGuard AI — Complete Setup Guide (Windows)

This guide assumes a fresh Windows machine with Anaconda Python already installed.

---

## Step 1: Install PostgreSQL

Download and install from: https://www.postgresql.org/download/windows/

During installation:
- Set password for `postgres` user (remember this!)
- Keep default port: **5432**
- Check "Add to PATH" if prompted

After installation, verify it's running:
```cmd
psql -U postgres -c "SELECT version();"
```

If PostgreSQL is installed but not running:
```cmd
net start postgresql-x64-15
```
(Replace `15` with your version number, e.g., `16`, `17`)

---

## Step 2: Install Redis

Redis doesn't have an official Windows build. Use one of these options:

**Option A: Memurai (Redis-compatible, recommended for Windows)**
- Download from: https://www.memurai.com/get-memurai
- Install and it runs as a Windows service automatically

**Option B: WSL (Windows Subsystem for Linux)**
```cmd
wsl --install
```
Then inside WSL:
```bash
sudo apt update
sudo apt install redis-server -y
sudo service redis-server start
redis-cli ping
```

**Option C: Docker (if you have Docker Desktop)**
```cmd
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

Verify Redis is running:
```cmd
redis-cli ping
```
Should respond: `PONG`

---

## Step 3: Install Node.js

Download LTS from: https://nodejs.org/en/download/
- Install with default settings
- Verify:
```cmd
node --version
npm --version
```

---

## Step 4: Create the Database

Open a command prompt:

```cmd
psql -U postgres
```

Inside the PostgreSQL shell:
```sql
CREATE DATABASE mediguard;
CREATE USER mediguard WITH PASSWORD 'mediguard123';
GRANT ALL PRIVILEGES ON DATABASE mediguard TO mediguard;
\c mediguard
GRANT ALL ON SCHEMA public TO mediguard;
\q
```

Now run the schema and migrations:
```cmd
cd "D:\MediGuard AI"
psql -U mediguard -d mediguard -f schema.sql
psql -U mediguard -d mediguard -f migrations/002_feedback_loop.sql
psql -U mediguard -d mediguard -f migrations/003_alert_dispatches.sql
psql -U mediguard -d mediguard -f migrations/004_patient_responses.sql
psql -U mediguard -d mediguard -f migrations/005_consultations_and_notes.sql
psql -U mediguard -d mediguard -f migrations/006_agent_actions.sql
```

---

## Step 5: Install Python Dependencies

```cmd
cd "D:\MediGuard AI\vitals-service"
pip install -r requirements.txt

cd "D:\MediGuard AI\agents"
pip install -r requirements.txt

cd "D:\MediGuard AI\dispatcher"
pip install -r requirements.txt

cd "D:\MediGuard AI\patient-api"
pip install -r requirements.txt
```

---

## Step 6: Install Node.js Dependencies

```cmd
cd "D:\MediGuard AI\backend"
npm install

cd "D:\MediGuard AI\doctor-dashboard"
npm install

cd "D:\MediGuard AI\dashboard"
npm install
```

---

## Step 7: Configure Environment Files

### Vitals Service
```cmd
cd "D:\MediGuard AI\vitals-service"
copy .env.example .env
```
Edit `vitals-service/.env`:
```
DATABASE_URL=postgresql://mediguard:mediguard123@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
VITALS_CACHE_TTL=60
```

### Agents
```cmd
cd "D:\MediGuard AI\agents"
copy .env.example .env
```
Edit `agents/.env`:
```
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
```

### Dispatcher
```cmd
cd "D:\MediGuard AI\dispatcher"
copy .env.example .env
```
Edit `dispatcher/.env`:
```
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
```

### Patient API
```cmd
cd "D:\MediGuard AI\patient-api"
copy .env.example .env
```
Edit `patient-api/.env`:
```
DATABASE_URL=postgresql://mediguard:mediguard123@localhost:5432/mediguard
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-your-key-here
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
DASHBOARD_BASE_URL=http://localhost:3000
PORT=8001
```

> **Note:** Twilio and SendGrid are optional. The system works without them — SMS/email just won't be delivered. The Anthropic API key IS required for the orchestrator and patient messaging.

---

## Step 8: Run the Application

Open **7 separate command prompt windows** and run each service:

### Terminal 1: Vitals Ingestion Service
```cmd
cd "D:\MediGuard AI\vitals-service"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Multi-Agent System
```cmd
cd "D:\MediGuard AI"
python -m agents
```

### Terminal 3: Alert Dispatcher
```cmd
cd "D:\MediGuard AI"
python -m dispatcher
```

### Terminal 4: Patient API
```cmd
cd "D:\MediGuard AI\patient-api"
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 5: Feedback Backend
```cmd
cd "D:\MediGuard AI\backend"
npm run dev
```

### Terminal 6: Doctor Dashboard
```cmd
cd "D:\MediGuard AI\doctor-dashboard"
npm run dev
```

### Terminal 7: Mock Data Generator (starts sending fake patient data)
```cmd
cd "D:\MediGuard AI\vitals-service"
python mock_generator.py
```

---

## Step 9: Access the Dashboards

| Dashboard | URL |
|-----------|-----|
| Doctor Dashboard | http://localhost:3000 |
| Vitals API Docs | http://localhost:8000/docs |
| Patient API Docs | http://localhost:8001/docs |
| Feedback API | http://localhost:3001 |

---

## Troubleshooting

### "Connect call failed ('127.0.0.1', 5432)"
PostgreSQL is not running. Start it:
```cmd
net start postgresql-x64-15
```
Or check Windows Services (`services.msc`).

### "Connection refused" on port 6379
Redis is not running. Start your Redis service (Memurai, Docker, or WSL).

### "ANTHROPIC_API_KEY not set" or LLM errors
Get an API key from https://console.anthropic.com/ and add it to your `.env` files.

### "ModuleNotFoundError: No module named 'xxx'"
You missed installing dependencies. Run:
```cmd
pip install -r requirements.txt
```
in the relevant service directory.

### "pydantic_settings" import error
```cmd
pip install pydantic-settings
```

### Port already in use
Kill the process using the port:
```cmd
netstat -ano | findstr :8000
taskkill /PID <pid_number> /F
```

### psql not recognized
Add PostgreSQL bin to your PATH:
```cmd
set PATH=%PATH%;C:\Program Files\PostgreSQL\15\bin
```
Or use the full path: `"C:\Program Files\PostgreSQL\15\bin\psql.exe"`

---

## Minimal Run (without external APIs)

If you just want to see the system work without Twilio/SendGrid/Anthropic:

1. Start PostgreSQL + Redis
2. Create database + run schema
3. Start vitals-service (Terminal 1)
4. Start mock_generator (Terminal 7)
5. Open http://localhost:8000/docs and watch vitals flow in

The agents and orchestrator need the Anthropic API key to synthesize alerts. Everything else (Twilio, SendGrid) is optional and degrades gracefully.

---

## Quick Verification Checklist

After starting all services, verify each is healthy:

```cmd
curl http://localhost:8000/api/health
curl http://localhost:8001/api/health
curl http://localhost:3001/api/health
```

All should return `{"status": "ok", ...}`

Then start the mock generator and watch the agent terminal — you should see alerts firing within 10-20 seconds as anomalies are injected.
