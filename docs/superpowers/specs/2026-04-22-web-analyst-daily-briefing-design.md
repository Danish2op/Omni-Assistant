# Design Spec: Web Analyst & Daily Briefing Engine

## 1. Overview
This project introduces two major cognitive and UX enhancements to Omni-Agent:
1. **The Broad Web Analyst:** Expands the Analyst Agent's capabilities beyond financial RSS feeds by integrating real-time DuckDuckGo web search. 
2. **Proactive Daily Briefing Engine:** Automatically cross-references tasks, news, and memory to generate a concise, personalized insight paragraph displayed on the dashboard upon load.

These enhancements will be accomplished entirely with free tools, requiring no new API keys.

---

## 2. Part 1: The Broad Web Analyst

### Architecture & Components
- **New Tool (`app/tools/web_search.py`):** Uses the `duckduckgo-search` library to fetch search results from the open web silently.
- **Analyst Agent (`app/agents/analyst.py`):** Dynamically decides whether to invoke the RSS cache (for strictly financial/market queries) or the new `web_search.py` tool (for general knowledge, tech news, world events).
- **Cognitive Router (`app/agents/router.py`):** The system prompt will be updated to explicitly route all general research, news, and informational search intents to the `ANALYST`, removing the restriction that Analyst is purely for "finance". 

### Error Handling
- The DuckDuckGo search is subject to rate-limiting since it is a free endpoint.
- If an HTTP or rate-limit error occurs, the `web_search.py` tool will return a graceful failure string. The Analyst will synthesize: *"I am currently unable to reach the live web for that search, but..."* instead of throwing a stack trace.

---

## 3. Part 2: Proactive Daily Briefing Engine

### Architecture & Components
- **New FastAPI Endpoint (`GET /api/briefing`):** A new dedicated route in `main.py` that orchestrates the data gathering.
- **Synthesis Engine:** The `/api/briefing` endpoint will fetch:
  1. All pending tasks from the `tasks` table.
  2. The top 3 cached news headlines from the RSS tool.
  3. Contextual hints from the `knowledge_base` (if applicable).
  All three data points will be injected into a strict, single Gemini API call prompt that asks for a 2-3 sentence cohesive "Morning Brief".
- **Next.js Integration (`frontend/src/components/Dashboard.tsx`):** A new React component `BriefingPanel` will be implemented. It will fetch from `/api/briefing` strictly on initial mount (`useEffect` with empty dependency array) and display a glassmorphic "Insight" card above the main conversation UI.

### Error Handling
- To prevent UI stalling, the `/api/briefing` endpoint will have a strict timeout.
- If the LLM call fails or times out, the backend instantly returns a hardcoded fallback string (e.g., *"Good morning. You have [X] pending tasks down below."*).
- The frontend card will show a neural-pulse loading state until the payload arrives.

---

## 4. Constraint Checklist
- **No Schema Changes:** The Supabase schema remains identical.
- **No New Keys Needed:** Relies on Gemini and the free `duckduckgo-search` lib.
- **Zero Hallucination Tolerance:** The Morning Brief must strictly base its correlations on the retrieved tasks and news.
