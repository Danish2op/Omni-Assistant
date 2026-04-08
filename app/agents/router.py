import json
from app.core.llm import GeminiClient


ROUTER_SYSTEM_PROMPT = """You are the High-Precision Router for Omni-Assistant. Your mission is to eliminate routing failures by transforming user input into surgical technical intents.

STRICT HIERARCHY OF INTENTS:
1. ARCHIVIST: Any mention of "my", "I", "remember", "recall", "stored", "notes", or queries about personal goals and past events.
2. ANALYST: Any mention of "news", "market", "stock", "price", "trend", "company", or financial analysis.
3. ORGANIZER: Any mention of "schedule", "task", "remind", "calendar", "todo", or time-management.
4. GENERAL: Only if NO other technical intent is detected. Basic greetings or generic meta-questions.

FEW-SHOT DECISION MATRIX:
- "What do I have to win?" -> {"intent": "ARCHIVIST", "refined_query": "Search knowledge base for goals, requirements, or criteria to win the hackathon", "reasoning": "User is asking about personal goals/stored info."}
- "What is the price of BTC?" -> {"intent": "ANALYST", "refined_query": "Latest BTC price and market data", "reasoning": "Market data request."}
- "Remind me to call Mom" -> {"intent": "ORGANIZER", "refined_query": "Create a task to call Mom", "reasoning": "Task creation request."}
- "Who are you?" -> {"intent": "GENERAL", "refined_query": "explain system capabilities", "reasoning": "System identity query."}

OUTPUT REQUIREMENT:
You MUST output ONLY a valid JSON object in this exact format, with no additional text or markdown formatting:
{
  "intent": "CATEGORY", 
  "refined_query": "An expanded search query optimized for the sub-agent's local tools", 
  "reasoning": "short explanation"
}
"""


class RouterAgent:
    def __init__(self):
        self.llm = GeminiClient()

    def route_request(self, user_input: str) -> dict:
        """
        Classify the user's input into an intent category using a structured Decision Matrix.
        """
        raw_response = self.llm.generate_response(
            prompt=user_input,
            system_instruction=ROUTER_SYSTEM_PROMPT
        )

        # Clean the response — strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
            # Support both processed_query and refined_query for backward/forward compatibility
            if "refined_query" in result and "processed_query" not in result:
                result["processed_query"] = result["refined_query"]
            return result
        except json.JSONDecodeError:
            return {
                "intent": "UNKNOWN",
                "reasoning": f"Failed to parse LLM response: {raw_response}",
                "processed_query": user_input
            }
