<p align="center">
  <img src="assets/banner.png" alt="Omni-Agent Neural Hub" width="100%" />
</p>

<h1 align="center">🧠 Omni-Agent</h1>

<p align="center">
  <strong>A Cognitive AI Assistant powered by Gemini 2.5 — with multi-agent orchestration, real-time financial intelligence, persistent memory, and task automation.</strong>
</p>

<p align="center">
  <a href="https://omni-jet-six.vercel.app">
    <img src="https://img.shields.io/badge/Live%20Demo-Visit%20App-00d4ff?style=for-the-badge&logo=vercel" alt="Live Demo" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0--COGNITIVE-blueviolet?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/badge/backend-FastAPI-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/frontend-Next.js%2016-black?style=for-the-badge&logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-4285F4?style=for-the-badge&logo=google" alt="Gemini" />
  <img src="https://img.shields.io/badge/database-Supabase-3FCF8E?style=for-the-badge&logo=supabase" alt="Supabase" />
  <img src="https://img.shields.io/badge/deploy-Render%20%2B%20Vercel-000?style=for-the-badge" alt="Deploy" />
</p>

---

## ✨ What is Omni-Agent?

Omni-Agent is a **production-grade AI assistant** that goes beyond simple chatbots. It features a **Cognitive Router** that decomposes natural language into structured execution plans, dispatching tasks to specialized sub-agents that work together to deliver precise, actionable results.

Ask it to _"check today's financial news and create a task if anything relates to my portfolio"_ — and it will:
1. 📰 Fetch live news from 25+ Indian financial RSS feeds
2. 🔍 Cross-reference findings with your existing tasks
3. ✅ Automatically create a new task with the relevant insight

All in a single conversation turn.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                     │
│              Dashboard.tsx (Tailwind + Framer Motion)    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                   FASTAPI BACKEND                       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │             🧠 COGNITIVE ROUTER                 │    │
│  │   Decomposes queries into Execution Plans       │    │
│  │   Emits: intent + action + keywords             │    │
│  └────┬────────┬────────┬────────┬─────────────────┘    │
│       │        │        │        │                      │
│  ┌────▼──┐ ┌───▼───┐ ┌──▼───┐ ┌──▼─────┐               │
│  │ 📊   │ │ 📚   │ │ ✅  │ │ 💬    │               │
│  │Analyst│ │Archiv.│ │Organ.│ │General │               │
│  └───┬───┘ └───┬───┘ └──┬───┘ └────────┘               │
│      │         │        │                               │
│  ┌───▼───┐ ┌───▼───┐ ┌──▼────┐                         │
│  │RSS/   │ │Supa-  │ │Supa-  │                         │
│  │News   │ │base   │ │base   │                         │
│  │Cache  │ │KB     │ │Tasks  │                         │
│  └───────┘ └───────┘ └───────┘                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │       🔄 MODEL FALLBACK CHAIN (LLM Core)       │    │
│  │  gemini-2.5-flash → 2.5-flash-lite → 2.0-flash │    │
│  │         Auto-retry on quota exhaustion           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Features

### 🧠 Cognitive Routing
The Router doesn't just classify intent — it generates a full **Execution Plan** with `action` and `keywords` for each step. This enables:
- **Single-step dispatch**: No redundant LLM calls inside agents
- **Multi-step orchestration**: _"Get news and create a task"_ → Analyst → Organizer
- **Ambiguity detection**: Vague input like _"Tell me more"_ triggers a clarification request

### 📊 Financial Analyst
- Fetches live data from **25+ Indian financial RSS feeds** (Moneycontrol, CNBC, ET Markets, NDTV Profit, etc.)
- **Zero-latency**: Background worker pre-caches news every 60 seconds using `AsyncIOScheduler`
- Delivers surgical, source-linked briefings — not generic summaries

### 📚 Memory Archivist
- **Store** facts, preferences, and notes in Supabase `knowledge_base`
- **Retrieve** with keyword-scoped search using DB-level `ilike` filtering
- **No-hallucination guard**: Returns _"I don't have records about that"_ instead of fabricating answers

### ✅ Task Organizer
- **Create** tasks with LLM-extracted names, due dates, and priorities
- **List** all tasks with formatted output (strikethrough for completed)
- **Filter** tasks by keyword — _"tasks related to stocks"_ returns only matching results
- **Update** task status (mark as completed)

### 🔄 Resilient LLM Core
- **4-model fallback chain**: If one model hits quota, the system automatically tries the next
- `gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-2.0-flash` → `gemini-2.0-flash-lite`
- **None-safety wrappers**: Blocked/empty responses never crash the system
- Zero user-facing technical errors — all failures produce helpful, human-readable messages

### 🎨 Premium Frontend
- Built with **Next.js 16**, **Tailwind CSS 4**, and **Framer Motion**
- Glassmorphic dark-mode dashboard with animated neural-pulse loading states
- Real-time markdown rendering with `react-markdown` + `remark-gfm`
- Responsive sidebar with conversation management

---

## 📂 Project Structure

```
Omni-Agent/
├── main.py                      # FastAPI orchestrator + lifespan events
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render deployment config
├── supabase_schema.sql          # Knowledge base schema
├── tasks_schema.sql             # Tasks table schema
│
├── app/
│   ├── agents/
│   │   ├── router.py            # 🧠 Cognitive Router (Reasoning Engine)
│   │   ├── analyst.py           # 📊 Financial news pipeline
│   │   ├── archivist.py         # 📚 Memory store/retrieve
│   │   ├── organizer.py         # ✅ Task CRUD + filtering
│   │   └── general.py           # 💬 Greetings + synthesis
│   ├── core/
│   │   ├── llm.py               # 🔄 Gemini client + fallback chain
│   │   └── database.py          # 🗄️ Supabase client + search
│   └── tools/
│       └── news_api.py          # 📰 RSS fetcher + background cache
│
├── frontend/
│   ├── src/
│   │   └── components/
│   │       └── Dashboard.tsx    # 🎨 Main UI component
│   ├── package.json
│   └── next.config.ts
│
└── assets/
    └── banner.png               # README banner
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google AI Studio](https://aistudio.google.com/) API key
- A [Supabase](https://supabase.com/) project

### 1. Clone & Setup Backend

```bash
git clone https://github.com/Danish2op/Omni-Assistant.git
cd Omni-Assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root:

```env
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
```

### 3. Setup Database

Run these SQL commands in your Supabase SQL Editor:

```sql
-- Knowledge Base (Memory)
CREATE TABLE knowledge_base (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    category TEXT,
    content TEXT,
    metadata JSONB
);

-- Tasks
CREATE TABLE tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name TEXT NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium'
);
```

### 4. Run Backend

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Visit `http://localhost:3000` 🎉

---

## 🌐 Deployment

### Backend → [Render](https://render.com/)

The `render.yaml` is pre-configured. Connect your GitHub repo and set environment variables:

| Variable | Value |
|----------|-------|
| `GOOGLE_API_KEY` | Your Gemini API key |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase anon key |

### Frontend → [Vercel](https://vercel.com/)

Import the `frontend/` directory and set:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your Render backend URL (no trailing slash) |

---

## 🧪 Stress Test Results

These are verified against the production build:

| Test Case | Query | Expected | Result |
|-----------|-------|----------|--------|
| **List Tasks** | _"What tasks do I have today?"_ | All tasks listed | ✅ Pass |
| **Filter Tasks** | _"Tasks related to stocks?"_ | Only stock-related tasks | ✅ Pass |
| **Empty Memory** | _"What do I remember about quantum physics?"_ | "I don't have records" | ✅ Pass |
| **Ambiguous Input** | _"Tell me more."_ | Clarification request | ✅ Pass |
| **Multi-Step Chain** | _"Get news and create a task"_ | Analyst → Organizer | ✅ Pass |

---

## 🛡️ Resilience Features

| Feature | Description |
|---------|-------------|
| **Model Fallback** | 4-model chain auto-retries on 429/503 errors |
| **None-Safety** | LLM responses are always strings, never `None` |
| **DB Error Boundaries** | Supabase timeouts return `[]`, not crashes |
| **No Technical Leakage** | Users see _"Could you try rephrasing?"_, not stack traces |
| **CLARIFY Handler** | Ambiguous input gets a polite follow-up, not a crash |
| **Background Caching** | News is always pre-fetched — no request-time latency |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Google Gemini 2.5 Flash (with fallback chain) |
| **Backend** | Python, FastAPI, Uvicorn |
| **Frontend** | Next.js 16, React 19, TypeScript |
| **Styling** | Tailwind CSS 4, Framer Motion |
| **Database** | Supabase (PostgreSQL) |
| **News** | 25+ Indian Financial RSS Feeds |
| **Scheduler** | APScheduler (AsyncIOScheduler) |
| **Deploy** | Render (backend) + Vercel (frontend) |

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/Danish2op">Danish Sharma</a>
</p>
