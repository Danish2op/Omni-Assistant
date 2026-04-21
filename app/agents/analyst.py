from app.tools.news_api import NewsTool
from app.tools.web_search import WebSearchTool
from app.core.llm import GeminiClient


ANALYST_SYSTEM_PROMPT = """You are a High-Precision Research Analyst. Your MISSION is to provide surgical, evidence-based briefings based on the provided search context.

CONSTRAINTS:
1. DIRECT ANSWER FIRST: You must answer the user's specific question in the very first sentence.
2. VERIFIABLE EVIDENCE: Every single claim or trend you mention must be immediately followed by a clickable source link (e.g., [Source: CNBC](URL) or [Source: DuckDuckGo](URL)).
3. SURGICAL PRECISION: Do not provide a general overview unless specifically asked. Focus purely on the target entity or subject.
4. NO FLUFF: Avoid introductory fillers or capability explanations.

Data provided in 'Raw Research Data' is your ONLY source for current news and facts. Use general knowledge only for stable context."""


class AnalystAgent:
    def __init__(self):
        self.news_tool = NewsTool()
        self.web_search_tool = WebSearchTool()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, processed_query: str = None) -> str:
        """
        Surgical Research Pipeline: Fetch Research Data → Direct Response → Verifiable Sources.
        """
        effective_query = processed_query if processed_query else user_input

        # Determine if query is financial/market-related or general
        financial_keywords = ['stock', 'market', 'price', 'nifty', 'sensex', 'financial', 'shares', 'investing']
        is_financial = any(kw in effective_query.lower() for kw in financial_keywords)

        if is_financial:
            # Action A.1: Fetch news using RSS NewsTool
            raw_news = self.news_tool.fetch_latest_news(query=effective_query, limit=15)

            # Format raw news into a readable string for the LLM
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
                news_text = "ERROR: No recent news data found in Indian financial RSS streams for this specific query."
        else:
            # Action A.2: Fetch general info using WebSearchTool
            news_text = self.web_search_tool.search(query=effective_query, limit=3)

        # Action B: Synthesis with Direct Answer Constraint
        synthesis_prompt = (
            f"User Question: {user_input}\n\n"
            f"Raw Research Data:\n{news_text}\n"
        )

        return self.llm.generate_response(
            prompt=synthesis_prompt,
            system_instruction=ANALYST_SYSTEM_PROMPT
        )
