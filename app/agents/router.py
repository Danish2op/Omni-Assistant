import json
from app.core.llm import GeminiClient


ROUTER_SYSTEM_PROMPT = """You are the High-Precision Router for Omni-Assistant. Your mission is to decompose user input into a sequence of technical execution steps. 

STRICT OUTPUT RULE: You MUST output ONLY a valid JSON object. No markdown code blocks, no preamble, no explanation.

STRICT HIERARCHY OF INTENTS:
1. ARCHIVIST: Personal memory retrieval/storage.
2. ANALYST: Financial news, stock data, market analysis, predictions.
3. ORGANIZER: Calendar, tasks, reminders.
4. GENERAL: Basic greetings or generic meta-questions.

MULTI-STEP WORKFLOWS:
If a user request requires multiple agents, return a "tasks" array.
- "Predict what sector to invest in and add a task" -> {"tasks": [{"intent": "ANALYST", "refined_query": "Latest Indian market sector trends and sentiment analysis"}, {"intent": "ORGANIZER", "refined_query": "Create investment task for the recommended sector"}]}

FEW-SHOT DECISION MATRIX:
- "Check news for 8 April and add task" -> {
    "tasks": [
      {"intent": "ANALYST", "refined_query": "Financial news 8 April 2026", "reasoning": "Fetch historical news data."},
      {"intent": "ORGANIZER", "refined_query": "Add task based on news synthesis", "reasoning": "Create task from news findings."}
    ]
  }
- "Remind me about color blue" -> {"tasks": [{"intent": "ARCHIVIST", "refined_query": "Recall information about color blue"}]}

FINAL OUTPUT FORMAT:
{
  "tasks": [
    {"intent": "CATEGORY", "refined_query": "optimized sub-query", "reasoning": "reasoning"}
  ],
  "reasoning": "overall plan"
}
"""


class RouterAgent:
    def __init__(self):
        self.llm = GeminiClient()

    def route_request(self, user_input: str) -> dict:
        """
        Decompose the user's input into one or more execution tasks with strict JSON handling.
        """
        try:
            raw_response = self.llm.generate_response(
                prompt=user_input,
                system_instruction=ROUTER_SYSTEM_PROMPT
            )

            # Ultra-Robust Cleaning
            cleaned = raw_response.strip()
            # Remove MD code blocks if present
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0] if "\n" in cleaned else cleaned[:-3]
            
            # Find the first { and last } to isolate the JSON
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]

            result = json.loads(cleaned)
            
            # Unify structure
            if "tasks" not in result:
                if "intent" in result:
                    result["tasks"] = [{
                        "intent": result["intent"],
                        "refined_query": result.get("refined_query", user_input),
                        "reasoning": result.get("reasoning", "Single step")
                    }]
                else:
                    raise ValueError("JSON missing intent/tasks")
            
            return result

        except Exception as e:
            # Atomic Fallback
            return {
                "tasks": [{
                    "intent": "GENERAL",
                    "refined_query": user_input,
                    "reasoning": f"Router parsing failure: {str(e)}"
                }],
                "reasoning": "Routed to GENERAL due to internal processing error."
            }
