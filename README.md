<p align="center">
  <img src="assets/banner.png" alt="Omni-Agent V2 Neural Hub" width="100%" />
</p>

<h1 align="center">🧠 Omni-Agent V2</h1>

<p align="center">
  <strong>A Multi-Agent, Multi-Model Cognitive Hub powered by OpenRouter — featuring sequential orchestration, advanced web intelligence, and deep-memory retrieval.</strong>
</p>

<p align="center">
  <a href="https://omni-v2-nu.vercel.app">
    <img src="https://img.shields.io/badge/Live%20Demo-Visit%20App-00d4ff?style=for-the-badge&logo=vercel" alt="Live Demo" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0--COGNITIVE-blueviolet?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/badge/backend-FastAPI-009688?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/frontend-Next.js%2015-black?style=for-the-badge&logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/Models-DeepSeek--R1%20%7C%20Llama%203.3-orange?style=for-the-badge" alt="Models" />
  <img src="https://img.shields.io/badge/Search-Tavily%20AI-blue?style=for-the-badge" alt="Tavily" />
</p>

---

## ✨ What's New in V2?

Omni-Agent V2 is a complete architectural overhaul of the original system. It moves away from single-intent responses toward a **Multi-Agent Orchestration** model that can decompose, execute, and synthesize complex, multi-part requests.

### 🔄 Multi-Intent Decompression
V2 can now handle compound prompts like: 
> *"Research the latest Nvidia earnings, store a note about their AI revenue, and set a task to review my portfolio tomorrow."*

The system will:
1. 🔍 Decompose the prompt into 3 distinct atomic tasks.
2. 🔄 Execute them sequentially using specialized sub-agents.
3. 📝 Synthesize a final unified response with all actions confirmed.

---

## 🏗️ Architecture: Multi-Agent & Multi-Model

V2 implements a "Decoupled Cognitive Pipeline" where the model is chosen based on the task complexity:

### 1. 🧠 Cognitive Router (The Orchestrator)
The Router uses high-reasoning models (**Llama 3.3 70B** or **Gemma 4**) to analyze the user's prompt. It doesn't just guess intent—it generates a structured **Execution Plan** consisting of multiple sub-tasks.

### 2. 📊 Specialized Agents
*   **Researcher (DeepSeek-R1 / QwQ-32B)**: Optimized for deep reasoning and web-synthesis.
*   **Archivist (Llama 3.3)**: Manages semantic memory storage and category-based retrieval.
*   **Organizer (Llama 3.3)**: Handles structured task CRUD and deadline extraction.
*   **Coder (Qwen 2.5 Coder)**: Specialized for technical queries and code generation.

### 3. 🔄 Resilient Model Fallback
V2 uses a **Per-Role Fallback Cascade** via OpenRouter. If the primary model for a role is rate-limited or unavailable, the system automatically tries 2-3 secondary models in real-time, ensuring zero downtime for the user.

---

## 🚀 Key Features

### 🔍 Advanced Web Intelligence (Tavily AI)
Legacy DuckDuckGo search has been replaced with **Tavily AI**.
*   **Advanced Search Depth**: Fetches high-fidelity technical and financial data.
*   **Surgical Precision**: Delivers source-linked citations for every factual claim.
*   **Link Verification**: Automatically filters out broken or irrelevant links.

### 📚 V2 Memory Engine (Memory Archivist)
The memory system has been upgraded to a structured **Cognitive Store**:
*   **Category-Scoped Search**: Retrieve information specifically from `finance`, `personal`, `work`, or `interview` categories.
*   **JSONB Metadata**: Stores rich context, source URLs, and timestamps for every memory.
*   **Keyword Extraction**: Automated tag generation for faster, more accurate retrieval.

### ✅ Task Orchestration
*   Extracts priorities and due dates from natural language.
*   Supports task filtering by keyword and category.
*   Interactive task status updates via the unified dashboard.

---

## 📂 Project Structure

```
Omni-Agent/
├── main_v2.py                   # 🚀 V2 Multi-Intent Orchestrator
├── requirements.txt             # Updated with Tavily & OpenRouter deps
├── render.yaml                  # Render deployment configuration
│
├── app/
│   ├── agents/
│   │   ├── v2_router.py         # 🧠 Multi-Intent Reasoning Engine
│   │   ├── v2_analyst.py        # 🔍 Tavily-powered Research Agent
│   │   ├── v2_archivist.py      # 📚 Category-based Memory Agent
│   │   └── v2_organizer.py      # ✅ Advanced Task Manager
│   ├── core/
│   │   ├── llm_v2.py            # 🔄 Multi-Model Client (Fallback Chain)
│   │   └── database_v2.py       # 🗄️ Enhanced Supabase V2 Client
│   └── tools/
│       └── tavily_search.py     # 🌐 Tavily API Integration
│
├── frontend/
│   ├── src/
│   │   └── components/
│   │       └── Dashboard.tsx    # 🎨 V2 Neural Dashboard
```

---

## ⚡ Tech Stack Evolution

| Layer | V1 (Legacy) | V2 (Cognitive Upgrade) |
| :--- | :--- | :--- |
| **LLM Gateway** | Google AI Studio | **OpenRouter (Multi-Provider)** |
| **Primary Models** | Gemini 1.5 Flash | **DeepSeek-R1, Llama 3.3, Qwen 2.5** |
| **Orchestration** | Single Intent | **Sequential Multi-Task Loop** |
| **Web Search** | DuckDuckGo | **Tavily AI (Advanced Mode)** |
| **Memory Search**| Global keyword | **Category-Scoped + Keywords** |
| **Database** | Supabase V1 | **Supabase V2 (Enhanced Schema)** |

---

## 🌐 Deployment

### Backend → [Render](https://render.com/)
1. Connect your GitHub repo.
2. Set `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and `TAVILY_API_KEY`.
3. The build will automatically use `main_v2.py`.

### Frontend → [Vercel](https://vercel.com/)
1. Import the `frontend/` directory.
2. Set `NEXT_PUBLIC_API_URL` to your Render backend address.
3. Deploy to the `v2-architecture` branch.

---

<p align="center">
  Built with ❤️ for the Next Generation of AI Agents by <a href="https://github.com/Danish2op">Danish Sharma</a>
</p>
