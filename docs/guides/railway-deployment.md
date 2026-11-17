# Railway Deployment Guide for Document Copilot

This guide outlines how to deploy Document Copilot to Railway as an institutional, production-ready research assistant.

## Architecture Topology

Document Copilot follows a two-tier service architecture on Railway, with durable state managed by hosted Supabase:

1. **Backend Service (`backend/`)**:
   - Runtime: Python 3.13 via `ghcr.io/astral-sh/uv` Docker image.
   - Server: FastAPI + Uvicorn.
   - Roles: Ingestion, full-text & vector hybrid search, PydanticAI streaming assistant, grounding validation.

2. **Frontend Service (`frontend/`)**:
   - Runtime: Node 22 (build stage) $\rightarrow$ Nginx Alpine (serve stage).
   - Artifact: Static single-page application (SPA).
   - Roles: Streaming chat UI, citation inspector shelf, Supabase authentication client.

3. **External Cloud Services**:
   - **Supabase**: Managed PostgreSQL 15+ instance with `pgvector`, Auth, and session pooler.
   - **OpenAI**: Embeddings (`text-embedding-3-small`) and generation (`gpt-4o-mini`).

---

## Deployment Steps

### 1. Create a Railway Project
1. Log in to [Railway](https://railway.app).
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Select the `document-copilot` repository.

### 2. Configure Backend Service
1. In the Railway project canvas, select the newly added service and rename it to `backend`.
2. Under **Settings**:
   - **Root Directory**: `backend`
   - **Build**: Uses `backend/Dockerfile` automatically.
   - **Healthcheck Path**: `/health`
3. Under **Variables**, add the following:
   ```env
   PORT=8000
   ALLOWED_ORIGINS=https://<your-frontend-service>.up.railway.app,http://localhost:5173
   DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@<HOST>:5432/postgres?sslmode=require
   SUPABASE_URL=https://<YOUR_PROJECT_REF>.supabase.co
   SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
   OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
   ```
4. Click **Deploy**.

### 3. Configure Frontend Service
1. In the same Railway project canvas, click **New Service** $\rightarrow$ **GitHub Repo** $\rightarrow$ Select `document-copilot`.
2. Rename the service to `frontend`.
3. Under **Settings**:
   - **Root Directory**: `frontend`
   - **Build**: Uses `frontend/Dockerfile` automatically.
4. Under **Variables**, configure:
   ```env
   VITE_API_URL=https://<your-backend-service>.up.railway.app
   VITE_SUPABASE_URL=https://<YOUR_PROJECT_REF>.supabase.co
   VITE_SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
   ```
5. Click **Deploy**.
6. Once deployed, copy the generated frontend domain (`https://frontend-production-xxxx.up.railway.app`) and ensure it is listed in the backend's `ALLOWED_ORIGINS` variable.

---

## Production Verification Checklist

1. **Health Endpoint**:
   ```bash
   curl -I https://<your-backend-service>.up.railway.app/health
   # Expected: HTTP/1.1 200 OK {"status":"healthy"}
   ```
2. **Company Index**:
   ```bash
   curl -s https://<your-backend-service>.up.railway.app/companies | jq .
   ```
3. **Database Migration**:
   Run database migrations inside Railway CLI or before initial deployment:
   ```bash
   railway run -s backend uv run alembic upgrade head
   ```
4. **Analyst Benchmark Suite**:
   Run the 10-question evaluation suite against the deployed backend:
   ```bash
   railway run -s backend uv run pytest tests/test_benchmark_eval.py
   ```
