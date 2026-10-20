# Unified Job Search & Application Management System

A centralized personal job-search assistant that connects job listings, company career websites, candidate profiles, resumes, and recruitment workflows into one unified workspace.

Designed with clean modular architecture suitable for B.Tech IT presentations, technical portfolio demonstrations, and real-world job hunting.

---

## 🛠️ Tech Stack

- **Frontend**: React 19, Vite, JavaScript, React Router DOM, Axios, Lucide Icons.
- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT, Bcrypt, PyPDF.
- **Database**: PostgreSQL 17 (Running on port 6314 locally), Alembic.
- **Testing**: Pytest, HTTPX, Vite build runner.

---

## 📁 Project Structure

```
unified-job-search/
├── frontend/             # React + Vite frontend application
│   ├── src/
│   │   ├── components/   # UI components (auth, jobs, applications, dashboard)
│   │   ├── pages/        # Application views
│   │   ├── services/     # Centralized API clients
│   │   ├── context/      # Auth & application state
│   │   └── App.jsx       # Routing & main layout
├── backend/              # FastAPI Python backend
│   ├── app/
│   │   ├── api/routes/   # REST endpoint routers
│   │   ├── core/         # Config, security, JWT
│   │   ├── db/           # Database session & models
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Matching, verification, resume parsing
│   ├── tests/            # Pytest test suite
│   └── requirements.txt
├── database/             # Migrations and seed scripts
├── docs/                 # System architecture, SRS, workflows
├── .env.example          # Environment variables template
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.13+
- Node.js v20+ / npm v10+
- PostgreSQL 17 (Service running on port 6314 or configured in `.env`)

### 2. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Backend Setup
```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest tests
uvicorn app.main:app --reload --port 8000
```
Interactive API docs will be available at: `http://localhost:8000/api/docs`

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend will be running at: `http://localhost:5173`

---

## 🧪 Running Tests

- **Backend Tests**: `cd backend && python -m pytest tests`
- **Frontend Build Validation**: `cd frontend && npm run build`
