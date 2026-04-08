import json
from app.core.llm import GeminiClient


ROUTER_SYSTEM_PROMPT = """You are the High-Precision Router for Omni-Assistant. Your mission is to decompose user input into a sequence of technical execution steps.

STRICT HIERARCHY OF INTENTS:
1. ARCHIVIST: Personal memory retrieval/storage.
2. ANALYST: Financial news, stock data, market analysis.
3. ORGANIZER: Calendar, tasks, reminders.
4. GENERAL: Basic greetings or generic meta-questions.

MULTI-STEP ORCHESTRATION:
If a user request requires multiple agents (e.g., "Check news AND THEN add a task"), you MUST return an array of tasks. 
- Example: "Get 8 April news and set a task to buy best stocks" -> {"tasks": [{"intent": "ANALYST", "refined_query": "news 8 April 2026"}, {"intent": "ORGANIZER", "refined_query": "Add task based on news findings"}]}

BACKWARD COMPATIBILITY:
For simple queries, you may return a single task object outside an array for simplicity, but the "tasks" array format is preferred for consistency.

FEW-SHOT DECISION MATRIX:
- "What do I have to win?" -> {"tasks": [{"intent": "ARCHIVIST", "refined_query": "Search knowledge base for goals, requirements, or criteria to win the hackathon"}]}
- "Get today's news and add a reminder for the IPO" -> {"tasks": [{"intent": "ANALYST", "refined_query": "Indian Stock Market news today"}, {"intent": "ORGANIZER", "refined_query": "Add reminder for upcoming IPO"}]}
- "Who are you?" -> {"tasks": [{"intent": "GENERAL", "refined_query": "explain system capabilities"}]}

OUTPUT REQUIREMENT:
You MUST output ONLY a valid JSON object in this exact format:
{
  "tasks": [
    {
      "intent": "CATEGORY", 
      "refined_query": "optimized sub-query", 
      "reasoning": "why this step?"
    }
  ],
  "reasoning": "overall plan reasoning"
}
"""


class RouterAgent:
    def __init__(self):
        self.llm = GeminiClient()

    def route_request(self, user_input: str) -> dict:
        """
        Decompose the user's input into one or more execution tasks.
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
            
            # Handle backward compatibility: unify into 'tasks' list
            if "tasks" not in result:
                if "intent" in result:
                    result["tasks"] = [{
                        "intent": result["intent"],
                        "refined_query": result.get("refined_query", result.get("processed_query", user_input)),
                        "reasoning": result.get("reasoning", "")
                    }]
                else:
                    raise ValueError("Malformed router output: No intent or tasks found.")
            
            return result
        except Exception as e:
            return {
                "tasks": [{
                    "intent": "UNKNOWN",
                    "reasoning": f"Fail: {str(e)}",
                    "refined_query": user_input
                }],
                "reasoning": "Fallback routing due to parsing error."
            }
