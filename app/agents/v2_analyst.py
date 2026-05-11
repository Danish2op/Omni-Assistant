"""
V2 Analyst Agent — Multi-Model Research Pipeline.

Uses RESEARCHER role for deep synthesis, GENERALIST for quick lookups.
Same tool integrations as V1 (NewsTool + WebSearchTool).
"""

from app.tools.news_api import NewsTool
from app.tools.tavily_search import TavilySearchTool
from app.core.llm_v2 import MultiModelClient, AgentRole


ANALYST_SYSTEM_PROMPT = """You are a High-Precision Research Analyst for Omni-Agent V2.

CONSTRAINTS:
1. DIRECT ANSWER FIRST: Answer the user's specific question in the very first sentence.
2. VERIFIABLE EVIDENCE: Every claim must be followed by a clickable source link using markdown `[Source Name](URL)`.
3. CLEAN STRUCTURE: Format the response elegantly using markdown. Use clear headings (`###`), bullet points for distinct facts or news items, and bold text for key entities. Do not output a giant wall of text.
4. SURGICAL PRECISION: Focus purely on the target entity or subject.
5. NO FLUFF: No introductory fillers, greetings, or capability explanations.

Data in 'Raw Research Data' is your ONLY source for current facts."""


class V2AnalystAgent:
    def __init__(self):
        self.news_tool = NewsTool()
        self.web_search_tool = TavilySearchTool()
        self.llm = MultiModelClient()

    def handle_query(self, user_input: str, processed_query: str = None) -> str:
        effective_query = processed_query if processed_query else user_input

        # Financial vs general routing
        financial_keywords = [
            "stock", "market", "price", "nifty", "sensex",
            "financial", "shares", "investing", "crypto", "bitcoin",
        ]
        is_financial = any(kw in effective_query.lower() for kw in financial_keywords)

        if is_financial:
            raw_news = self.news_tool.fetch_latest_news(query=effective_query, limit=15)
            if raw_news:
                news_text = "\n\n".join([
                    f"Source: {item['source']}\n"
                    f"Title: {item['title']}\n"
                    f"Summary: {item['summary']}\n"
                    f"Date: {item['date']}\n"
                    f"URL: {item['link']}"
                    for item in raw_news
                ])
            else:
                news_text = "No recent financial news found for this query."
        else:
            news_text = self.web_search_tool.search(query=effective_query, limit=3)

        synthesis_prompt = (
            f"User Question: {user_input}\n\n"
            f"Raw Research Data:\n{news_text}\n"
        )

        # Use RESEARCHER role for deep synthesis
        return self.llm.generate(
            prompt=synthesis_prompt,
            system_instruction=ANALYST_SYSTEM_PROMPT,
            role=AgentRole.RESEARCHER,
            max_tokens=2048,
        )
