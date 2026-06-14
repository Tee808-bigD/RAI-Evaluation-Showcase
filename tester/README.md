# ResearchSwarm — Microsoft Build AI Hackathon

**Theme 05: Agent Swarms** | 3-agent research pipeline built on AutoGen + Azure OpenAI

## Architecture

```
User Question
     │
     ▼
 [Planner Agent]          → Breaks question into 3 sub-tasks
     │
     ▼
 [Researcher Agent × 3]   → Bing search + LLM extraction per sub-task
     │
     ▼
 [Synthesizer Agent]      → Merges findings into a structured answer
     │
     ▼
 React Dashboard          → Live orchestration graph via WebSocket
```

## Stack

| Layer | Tech |
|-------|------|
| Agent framework | AutoGen AgentChat 0.4 |
| LLM | GPT-4o via Azure OpenAI |
| Web search | Bing Search API v7 |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18 + Vite |
| Deployment | Azure App Service + Azure Static Web Apps |

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/research-swarm
cd research-swarm
cp .env.example .env
# Fill in your Azure OpenAI + Bing API keys in .env
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
# Runs on http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

### 4. Azure keys you need

- **Azure OpenAI** — create a resource, deploy `gpt-4o`, grab endpoint + key
- **Bing Search API** — create via Azure portal → AI + Machine Learning → Bing Search

## Azure Deployment

```bash
# Backend → Azure App Service (B1 tier is fine for demo)
az webapp up --name research-swarm-api --runtime PYTHON:3.11

# Frontend → Azure Static Web Apps
npm run build
# Deploy /dist via Azure Static Web Apps GitHub action
```

Set all `.env` values as App Settings in your App Service.

## Team

| Name | Role |
|------|------|
| [Your Name] | Full-stack + AI |
