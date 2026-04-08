from app.tools.news_api import NewsTool
from app.core.llm import GeminiClient


ANALYST_SYSTEM_PROMPT = """You are a High-Precision Financial Research Analyst. Your MISSION is to provide surgical, evidence-based briefings.

CONSTRAINTS:
1. DIRECT ANSWER FIRST: You must answer the user's specific ticker or market question in the very first sentence.
2. VERIFIABLE EVIDENCE: Every single claim or trend you mention must be immediately followed by a clickable source link (e.g., [Source: CNBC](URL)).
3. SURGICAL PRECISION: Do not provide a general market overview unless specifically asked. Focus purely on the target company or sector.
4. NO FLUFF: Avoid introductory fillers or capability explanations.

Data provided in 'Raw Data' is your ONLY source for current news. Use general knowledge only for stable context."""


class AnalystAgent:
    def __init__(self):
        self.news_tool = NewsTool()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, processed_query: str = None) -> str:
        """
        Surgical Research Pipeline: Fetch Fetch → Direct Response → Verifiable Sources.
        """
        # Action A: Fetch news using refined keywords from the Router
        effective_query = processed_query if processed_query else user_input
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

        # Action B: Synthesis with Direct Answer Constraint
        synthesis_prompt = (
            f"User Question: {user_input}\n\n"
            f"Raw Research Data:\n{news_text}\n"
        )

        return self.llm.generate_response(
            prompt=synthesis_prompt,
            system_instruction=ANALYST_SYSTEM_PROMPT
        )
