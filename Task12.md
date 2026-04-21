# Task 12: Broad Web Analyst & Daily Briefing Engine Implementation Plan

## Context & Objective
Implement the features designed in `docs/superpowers/specs/2026-04-22-web-analyst-daily-briefing-design.md`. The goal is to safely extend the Analyst to use DuckDuckGo for general web searches and to introduce a proactive Daily Briefing endpoint without breaking existing production behavior.

## Execution Steps

### Step 1: Install Dependencies & Setup Tool
1. Run `pip install duckduckgo-search` to add strictly free, zero-key web search.
2. Update `requirements.txt`.
3. Create `app/tools/web_search.py` implementing `WebSearchTool` with rate-limit and error catching. It should return a string snippet of top results.

### Step 2: Empower the Analyst
1. Modify `app/agents/analyst.py`.
2. Integrate `WebSearchTool`.
3. Read the `refined_query` from the Router. If it explicitly contains financial or Indian market keywords (stock, market, price, Nifty, Sensex), use the existing RSS `NewsTool.get_market_brief()`.
4. If it's a general query, invoke `WebSearchTool.search()`, get the top 3 results, and pass them to Gemini to synthesize an answer.
5. Update the Analyst prompt to support answering general factual questions based on search context.

### Step 3: Upgrade the Cognitive Router
1. Modify `app/agents/router.py`.
2. Update the `ROUTER_SYSTEM_PROMPT` to broaden the `ANALYST` capabilities:
   - `"ANALYST: Actions = RESEARCH (Financial OR General Web Search)"`
   - `"ANALYST/RESEARCH: 'news', 'market', 'stocks', 'financial', 'who is', 'what happened with', 'latest on', 'search the web'"`
3. Add a Few-Shot example for a generic internet query to ensure the Router passes it to the Analyst.

### Step 4: The Daily Briefing Backend Engine
1. In `main.py` (or a dedicated router), add a new `GET /api/briefing` endpoint.
2. Gather data sequentially or concurrently:
   - Call `supabase.table("tasks").select("*").eq("status", "pending").execute()` to get pending tasks.
   - Get the top 3 headlines from the `NewsTool` cache.
3. Pass both datasets into a single `GeminiClient` call with a specific prompt: *"Synthesize a 2-3 sentence morning briefing connecting these active tasks to the current news if explicitly relevant. Do not hallucinate."*
4. Wrap the endpoint in a strict `try-except` block to return a hardcoded fallback string on timeout/error to prevent UI blocking.

### Step 5: Frontend Briefing Panel Activation
1. Modify `frontend/src/components/Dashboard.tsx`.
2. Add a `BriefingPanel` component at the top of the chat/task boards.
3. Add a `useEffect` hook to fetch from `/api/briefing` on initial load.
4. Build a sleek UI component (glassmorphic card) that displays the Briefing text. Show a neural loading pulse animation while the data is fetching.

## Verification Protocol (Stress Test)
1. **Web Search Test**: Ask *"What is the latest update on SpaceX's Starship?"* -> Verify it hits the web search tool, not the Indian financial RSS cache.
2. **Finance Test**: Ask *"How are Indian tech stocks doing?"* -> Verify it continues to use the instant RSS feed correctly.
3. **Briefing Endpoint Test**: Call `GET /api/briefing` manually -> Verify it responds within 5 seconds with a cohesive 3-sentence summary of tasks and news.
4. **Resilience Test**: Simulate a timeout or fake error in the `/api/briefing` -> Verify the Dashboard correctly displays the fallback string instead of crashing.
