# SEMANTIQ (セマンティック)
### Permission-Aware Organizational Knowledge Graph & GraphRAG Reasoning System

> *"Permission-aware reasoning over connected organizational knowledge."*

[![Backend Tests](https://img.shields.io/badge/pytest-44%20passed-emerald.svg)](backend/tests)
[![Evaluation Pass Rate](https://img.shields.io/badge/eval%20pass%20rate-100%25-emerald.svg)](backend/app/services/evaluation_service.py)
[![Permission Leakage](https://img.shields.io/badge/permission%20leakage-0.0%25-emerald.svg)](backend/tests/test_security_boundary.py)
[![Citation Validity](https://img.shields.io/badge/citation%20validity-100%25-indigo.svg)](backend/app/services/validation_service.py)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Gemini%20Live%20(gemini--3.6--flash)-blue.svg)](backend/app/services/llm_service.py)
[![Frontend Build](https://img.shields.io/badge/vite%20build-passing-emerald.svg)](frontend)

---

## 1. Executive Summary & Core Problem

Modern industrial enterprises (aerospace, precision manufacturing, industrial robotics) distribute operational information across heterogeneous silos:

```
Project C (PRJ-GAMMA)
   ↓ depends on
CNC-07 Milling Center (SYS-CNC-07)
   ↓ affected by
Incident 104 (INC-104 Spindle Thermal Excursion)
   ↓ related to
SOP-017 (Emergency Spindle Shutdown Protocol)
   ↓ recommends
Immediate Feed Hold & Dial Indicator Runout Inspection
```

### Why Traditional Vector RAG Fails:
1. **Relational Blindness**: Traditional semantic vector search retrieves isolated text chunks that match keyword embeddings, but cannot navigate multi-hop causal dependencies across projects, machines, incidents, teams, and policies.
2. **Permission Leakage Hazard**: Sending raw organizational data into LLM context windows creates security vulnerabilities. If restricted contracts, pricing formulas, or executive compensation records enter the model prompt, confidential data leaks through model outputs.
3. **Hallucinated Citations & Fabricated Grounding**: Ordinary chat agents often hallucinate document IDs, misattribute policy rules, or claim high confidence without verifiable evidence.

**SEMANTIQ** solves this with a **bounded-context, least-privilege GraphRAG architecture**. The LLM is treated strictly as an **untrusted reasoning worker** operating over an authorized, minimized context subgraph.

---

## 2. Core Architecture & Pipeline

```
                                USER QUERY
                                    ↓
                 ┌──────────────────────────────────────┐
                 │ 1. Server-Side Identity & Auth Gate  │
                 │    (HMAC Token Verification)         │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 2. Query Intent Classification       │
                 │    (Dependency / Impact / Policy)    │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 3. Pre-LLM Permission Filter Gate    │
                 │    (PUBLIC/INTERNAL/CONF./RESTRICTED)│
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 4. Bounded Graph Traversal           │
                 │    (NetworkX Authorized Subgraph)    │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 5. Scoped Hybrid Evidence Retrieval  │
                 │    (Project Isolation + Intent Match)│
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 6. Context Minimization Engine       │
                 │    (Zero-Leakage Authorized Context) │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 7. Google Gemini 3.6 Flash / LLM     │
                 │    (Structured JSON Synthesis)       │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 8. Claim ↔ Evidence Validation Engine │
                 │    (Citation Matching & Verification)│
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 9. Calibrated Confidence Scoring     │
                 │    (Grounding + Topology - Penalties)│
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 10. Human-in-the-Loop Action Hook    │
                 │     (Operator Approval Workflow)     │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │ 11. Auditable Query Ledger           │
                 │     (SQLite / PostgreSQL Trail)      │
                 └──────────────────────────────────────┘
```

---

## 3. Key Architectural Pillars

### A. Server-Side Identity & Role Resolution
- User identity is established through cryptographically signed session tokens (`Authorization: Bearer <token>`).
- Roles are resolved strictly **server-side**. Any client-supplied `role` parameter in request payloads or query parameters is explicitly ignored.
- In production (`APP_ENV=production`), unauthenticated requests are rejected with HTTP 401.

### B. Pre-LLM Zero-Leakage Permission Gate
- Permissions run **strictly before** graph traversal, document retrieval, or context construction.
- The LLM is never given raw organizational data and is never responsible for making authorization decisions.
- When an unauthorized user queries restricted topics, the restricted items are pruned before prompt assembly. The LLM context receives **0 tokens** of restricted data, producing a safe `"Insufficient authorized evidence"` response.

### C. Tri-Concept Separation (Graph Fact vs. Documentary Evidence vs. Synthesis)
- **Graph Fact**: A topological connection in the knowledge graph (e.g. `PRJ-DELTA` $\to$ `DEPENDS_ON` $\to$ `SYS-FURN-05`).
- **Documentary Evidence**: An indexed text excerpt (e.g. `EVID-DELTA-01` in `DOC-FURN-05`) explicitly substantiating a claim.
- **LLM Synthesis**: Grounded reasoning constrained by authorized facts. When graph relationships exist without direct text chunks, the system labels them as graph facts rather than inventing documentary citations.

### D. Citation Grounding & Hallucination Prevention
- Every factual claim generated by the reasoning engine must cite an explicit Evidence ID (e.g., `EVID-017-01`).
- The backend validation engine verifies that each cited ID:
  1. Actually exists in the evidence registry.
  2. Was actually retrieved in this query execution.
  3. Was authorized for the user's role.
  4. Directly corresponds to the claimed entities.

### E. Deterministic Confidence Model
Confidence is calculated deterministically by the application:
- **Evidence Quality (0–30 pts)**: Count and relevance scores of retrieved authorized evidence chunks.
- **Graph Path Strength (0–30 pts)**: Hop distance and topological strength of causal graph connections.
- **Citation Grounding (0–25 pts)**: Percentage of claims backed by verified evidence.
- **Entity Resolution (0–15 pts)**: Entity extraction completeness.
- **Unsupported Claim Penalty (-15 pts per unsupported claim)**.

---

## 4. Role & Classification Clearance Matrix

| Role | PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED | Description |
|---|:---:|:---:|:---:|:---:|---|
| **Administrator (`admin`)** | ✅ | ✅ | ✅ | ✅ | Full organizational clearance including contracts & compensation |
| **Operations Engineer (`operations_engineer`)** | ✅ | ✅ | ✅ | ❌ | Access to SCADA telemetry, maintenance SOPs, equipment limits |
| **Project Manager (`project_manager`)** | ✅ | ✅ | ✅ | ❌ | Access to cross-project dependencies, roadmaps, and systems |
| **Viewer / Auditor (`viewer`)** | ✅ | ✅ | ❌ | ❌ | Read-only access to general organizational registries |

---

## 5. Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Google Gemini API Key (from [Google AI Studio](https://aistudio.google.com/))

### 1. Backend Setup
```bash
# Navigate to backend and create virtual environment
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp ../.env.example .env
```

Edit `.env` to configure your Gemini API Key and settings:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
APP_ENV=development
PORT=8000
DATABASE_URL=sqlite:///./semantiq.db
AUTH_SECRET_KEY=your_secure_auth_secret_key
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Start the backend API server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 6. Running Tests & Benchmarks

### Automated Pytest Suite
```bash
# Run all backend unit, integration, and security tests
$env:PYTHONPATH="backend"; .\venv\Scripts\pytest backend/tests -v
```

### Automated Benchmark Evaluation (10 Golden Cases)
```bash
$env:PYTHONPATH="backend"; .\venv\Scripts\python -c "import asyncio; from app.services.evaluation_service import evaluation_service; res = asyncio.run(evaluation_service.run_evaluation()); print('Pass Rate:', res.pass_rate, '%')"
```

---

## 7. Production Deployment Guide

### Environment Variables for Production
| Variable | Description | Example |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API Key | `your_gemini_api_key` |
| `GEMINI_MODEL` | Gemini Model Identifier | `gemini-3.6-flash` |
| `APP_ENV` | Application Environment | `production` |
| `PORT` | Web Server Port | `8000` |
| `DATABASE_URL` | PostgreSQL or SQLite Connection String | `postgresql://user:pass@host:5432/semantiq` |
| `AUTH_SECRET_KEY` | High-Entropy Secret for Token Signing | `random_64_char_secret` |
| `CORS_ORIGINS` | Allowed Frontend Domain(s) | `https://semantiq.yourdomain.com` |
| `VITE_API_BASE_URL` | (Frontend) API Endpoint Base URL | `https://api.semantiq.yourdomain.com/api` |

### Deploying to Render / Railway / Fly.io

1. **Backend Deployment (FastAPI)**:
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Set environment variables as listed above.

2. **Frontend Deployment (Vercel / Netlify / Cloudflare Pages)**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Environment Variable: `VITE_API_BASE_URL=https://<your-backend-domain>/api`
