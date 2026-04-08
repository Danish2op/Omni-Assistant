from app.tools.news_api import NewsTool
from app.core.llm import GeminiClient


ANALYST_SYSTEM_PROMPT = """You are a Senior Financial Analyst working for Omni-Assistant. 
I will provide you with raw news data fetched from Indian financial news sources. 
Your job is to synthesize this into a professional, concise briefing for the user. 

Focus on:
1. Market Impact — How does this news affect markets or specific sectors?
2. Key Trends — What patterns or trends emerge from the data?
3. Bottom Line — A 2-3 sentence summary with actionable insight.

Format your response as a clean, readable briefing. Do NOT return raw JSON or data dumps.
If the news data is empty or irrelevant, say so honestly and provide general market context instead."""


class AnalystAgent:
    def __init__(self):
        self.news_tool = NewsTool()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str) -> str:
        """
        End-to-end pipeline: Fetch news → Synthesize with Gemini → Return briefing.

        Args:
            user_input: The user's financial/market question.

        Returns:
            A professional synthesized briefing string.
        """
        # Action A: Fetch news using keywords from user input
        raw_news = self.news_tool.fetch_latest_news(query=None, limit=15)

        # Format raw news into a readable string for the LLM
        if raw_news:
            news_text = "\n\n".join([
                f"Source: {item['source']}\n"
                f"Title: {item['title']}\n"
                f"Summary: {item['summary']}\n"
                f"Date: {item['date']}"
                for item in raw_news
            ])
        else:
            news_text = "No recent news data available from RSS feeds."

        # Action B: Send to Gemini with synthesis prompt
        synthesis_prompt = (
            f"Raw Data:\n{news_text}\n\n"
            f"User Question: {user_input}"
        )

        # Action C: Return the synthesized response
        response = self.llm.generate_response(
            prompt=synthesis_prompt,
            system_instruction=ANALYST_SYSTEM_PROMPT
        )

        return response
