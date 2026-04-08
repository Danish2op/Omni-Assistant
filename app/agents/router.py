import json
from app.core.llm import GeminiClient


ROUTER_SYSTEM_PROMPT = """You are the Router for Omni-Assistant. Your ONLY job is to classify user input into one of three categories.

Categories:
- ANALYST: Anything related to financial news, stock prices, market data, economic analysis, or investment queries.
- ARCHIVIST: Anything related to saving, storing, remembering, or retrieving personal notes, facts, or knowledge.
- ORGANIZER: Anything related to scheduling, calendar events, tasks, reminders, or to-do lists.
- GENERAL: Basic greetings, general conversation, or meta-questions about what the Omni-Assistant can do.

You MUST output ONLY a valid JSON object in this exact format, with no additional text, explanation, or markdown formatting:
{"intent": "CATEGORY", "reasoning": "short explanation"}

Examples:
User: "What is the price of Nvidia?"
Output: {"intent": "ANALYST", "reasoning": "User is asking about stock price which is financial market data."}

User: "Remember that my dog's name is Max."
Output: {"intent": "ARCHIVIST", "reasoning": "User wants to save a personal fact for later retrieval."}

User: "Schedule a meeting for tomorrow."
Output: {"intent": "ORGANIZER", "reasoning": "User wants to schedule a calendar event."}
"""


class RouterAgent:
    def __init__(self):
        self.llm = GeminiClient()

    def route_request(self, user_input: str) -> dict:
        """
        Classify the user's input into an intent category using Gemini.

        Args:
            user_input: The raw text message from the user.

        Returns:
            A dict with 'intent' and 'reasoning' keys.
        """
        raw_response = self.llm.generate_response(
            prompt=user_input,
            system_instruction=ROUTER_SYSTEM_PROMPT
        )

        # Clean the response — strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Remove opening ```json or ``` line
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError:
            return {
                "intent": "UNKNOWN",
                "reasoning": f"Failed to parse LLM response: {raw_response}"
            }
