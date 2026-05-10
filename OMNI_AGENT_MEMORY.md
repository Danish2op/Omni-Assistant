# 🧠 Omni-Agent: Project Memory Hub

This file tracks the collective intelligence, historical context, and architectural evolution of the **Omni-Agent** project. It is designed to be updated continuously as the project progresses.

---

## 💎 Project Identity & Vision
- **Core Concept**: A multi-agent "Neural Hub" that orchestrates specialized AI agents to handle real-time data, memory, and tasks.
- **Mission**: Move beyond passive chat to proactive, production-grade agentic automation.
- **Status**: `v3.0.0-COGNITIVE` (Active/Production)

---

## 🏗️ System Architecture

### 1. The Cognitive Router (`app/agents/router.py`)
- **Function**: Decomposes user queries into structured **Execution Plans**.
- **Output**: JSON containing `intent`, `action`, `keywords`, and `refined_query`.
- **Intents**: `ANALYST`, `ARCHIVIST`, `ORGANIZER`, `GENERAL`.

### 2. Specialized Agents
| Agent | Logic File | Core Responsibility |
|-------|------------|---------------------|
| **📊 Analyst** | `analyst.py` | Fetches news (RSS + DuckDuckGo) & synthesizes market briefings. |
| **📚 Archivist** | `archivist.py` | Manages persistent personal memory in Supabase `knowledge_base`. |
| **✅ Organizer** | `organizer.py` | Handles Task CRUD with smart extraction of dates and priorities. |
| **💬 General** | `general.py` | Synthesis, greetings, and handling ambiguity via `CLARIFY`. |

### 3. LLM Resilience Layer (`app/core/llm.py`)
- **Strategy**: 4-model fallback chain to handle rate limits/quota.
- **Chain**: `gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-2.0-flash` → `gemini-2.0-flash-lite`.

---

## 🛠️ Technical Stack
- **Backend**: FastAPI (Python 3.11+), Supabase (PostgreSQL), APScheduler.
- **Frontend**: Next.js 16 (App Router), Tailwind CSS 4, Framer Motion.
- **UI Aesthetic**: Glassmorphic Cyber-Noir / Neural Monolith.
- **External Tools**: 25+ Financial RSS feeds, DuckDuckGo Search.

---

## 📜 Historical Milestones (Synthesized Context)

### 🗓️ Foundation (Initial Build)
- Established core FastAPI structure and Supabase integration.
- Implemented the first iteration of the Router and Gemini client.

### 🗓️ The "Cognitive Hardening" Phase
- **Background Caching**: Implemented `AsyncIOScheduler` for zero-latency news retrieval.
- **None-Safety**: Wrapped all LLM calls to prevent crashes on empty/blocked responses.
- **Multi-Step Chains**: Router empowered to emit multi-task plans (e.g., "Get news and save a task").

### 🗓️ Web Analyst & Daily Briefing (Task 12)
- Integrated `duckduckgo-search` for general web context.
- Created the `/api/briefing` endpoint to proactively synthesize task/news summaries.
- Implemented the `BriefingPanel` in the frontend dashboard.

---

## 🛡️ Security & Ops Context
- **Deployment**: Render (Backend) + Vercel (Frontend).
- **Security Audit**: Environment variables audited and credentials rotated post-Vercel incident.
- **Environment**: `.env` used for `GOOGLE_API_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY`.

---

## 🚀 Active Roadmap & Backlog
- [ ] **Interactive Task Board**: Drag-and-drop status updates in the UI.
- [ ] **Voice Integration**: Adding speech-to-text for "Hands-Free" hub interaction.
- [ ] **Advanced Filtering**: Vector search for the Knowledge Base (moving beyond `ilike`).

---
*Memory last updated: 2026-05-10 | Current Chat: 1b557d30-3bcb-47f2-9a5f-b4d127410cf6*
