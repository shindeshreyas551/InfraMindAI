# InfraMind AI – Intelligent Endpoint Monitoring & AI Incident Analysis Platform (v1 MVP)

InfraMind AI is a real-time endpoint monitoring platform designed to monitor Windows machines, aggregate real system telemetry, store historical health data, and visualize live metrics through a web dashboard.

---

## Repository Architecture

```
InfraMind AI/
├── agent/       # Python Windows Monitoring Agent (psutil, Pydantic, persistent Device ID)
├── backend/     # FastAPI REST Service (Python, SQLAlchemy, JWT Auth, Swagger)
└── frontend/    # Next.js Web Dashboard (TypeScript, Tailwind CSS, live charts)
```

---

## Quick Start Guide

### 1. Windows Monitoring Agent (`/agent`)
```powershell
cd agent
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

### 2. FastAPI Backend Service (`/backend`)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```
- Swagger Documentation: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/health`
