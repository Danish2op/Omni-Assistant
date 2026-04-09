import json
from app.core.llm import GeminiClient


ROUTER_SYSTEM_PROMPT = """You are the Cognitive Router for Omni-Assistant. Your job is to decompose user input into an Execution Plan.

STRICT OUTPUT RULE: You MUST output ONLY a valid JSON object. No markdown, no preamble.

INTENT + ACTION VOCABULARY:
- ORGANIZER: Actions = CREATE, LIST, FILTER, UPDATE
- ARCHIVIST: Actions = STORE, RETRIEVE
- ANALYST: Actions = RESEARCH
- GENERAL: Actions = CHAT, CLARIFY

WHEN TO USE EACH ACTION:
- ORGANIZER/LIST: "show my tasks", "what do I have to do", "list tasks"
- ORGANIZER/FILTER: "tasks related to X", "tasks about Y" → extract keywords
- ORGANIZER/CREATE: "add a task", "remind me to", "create task"
- ORGANIZER/UPDATE: "mark X as done", "complete task X"
- ARCHIVIST/STORE: "remember that", "note that", "save this"
- ARCHIVIST/RETRIEVE: "what do I remember about", "recall", "what did I save"
- ANALYST/RESEARCH: "news", "market", "stocks", "financial"
- GENERAL/CLARIFY: vague/ambiguous input like "tell me more", "ok", "continue", "yes"
- GENERAL/CHAT: greetings, meta-questions about the system

OUTPUT FORMAT:
{
  "tasks": [
    {
      "intent": "ORGANIZER",
      "action": "FILTER",
      "keywords": ["stocks", "market"],
      "refined_query": "Filter tasks related to stocks and market"
    }
  ],
  "reasoning": "User wants filtered tasks"
}

FEW-SHOT EXAMPLES:

User: "What tasks do I have today?"
{"tasks": [{"intent": "ORGANIZER", "action": "LIST", "keywords": [], "refined_query": "List all current tasks"}], "reasoning": "User wants to see all tasks"}

User: "What tasks do I have related to stocks?"
{"tasks": [{"intent": "ORGANIZER", "action": "FILTER", "keywords": ["stocks", "stock", "investment", "market"], "refined_query": "Filter tasks related to stocks"}], "reasoning": "User wants tasks filtered by stock-related keywords"}

User: "Add a task to review HDFC quarterly results"
{"tasks": [{"intent": "ORGANIZER", "action": "CREATE", "keywords": [], "refined_query": "Create task: Review HDFC quarterly results"}], "reasoning": "User wants to create a new task"}

User: "What do I remember about my favorite color?"
{"tasks": [{"intent": "ARCHIVIST", "action": "RETRIEVE", "keywords": ["favorite color", "color"], "refined_query": "Retrieve memory about favorite color"}], "reasoning": "User wants to recall stored memory"}

User: "Remember that my favorite stock is Reliance"
{"tasks": [{"intent": "ARCHIVIST", "action": "STORE", "keywords": [], "refined_query": "Store: favorite stock is Reliance"}], "reasoning": "User wants to save a fact"}

User: "Check my news for today and tell me if any of it relates to my existing tasks."
{"tasks": [{"intent": "ANALYST", "action": "RESEARCH", "keywords": [], "refined_query": "Fetch latest financial news for today"}, {"intent": "ORGANIZER", "action": "LIST", "keywords": [], "refined_query": "List all tasks and compare with news findings"}], "reasoning": "Multi-step: fetch news then cross-reference with tasks"}

User: "Tell me more."
{"tasks": [{"intent": "GENERAL", "action": "CLARIFY", "keywords": [], "refined_query": "Ask user for clarification"}], "reasoning": "Ambiguous input, need clarification"}

User: "Hello"
{"tasks": [{"intent": "GENERAL", "action": "CHAT", "keywords": [], "refined_query": "Respond to greeting"}], "reasoning": "Simple greeting"}
"""


class RouterAgent:
    def __init__(self):
        self.llm = GeminiClient()

    def route_request(self, user_input: str) -> dict:
        """
        Decompose user input into an Execution Plan with intent, action, and keywords.
        """
        try:
            raw_response = self.llm.generate_response(
                prompt=user_input,
                system_instruction=ROUTER_SYSTEM_PROMPT
            )

            # Robust JSON cleaning
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0] if "\n" in cleaned else cleaned[:-3]
            
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]

            result = json.loads(cleaned)
            
            # Normalize: ensure tasks array exists
            if "tasks" not in result:
                if "intent" in result:
                    result["tasks"] = [{
                        "intent": result.get("intent", "GENERAL"),
                        "action": result.get("action", "CHAT"),
                        "keywords": result.get("keywords", []),
                        "refined_query": result.get("refined_query", user_input),
                    }]
                else:
                    raise ValueError("JSON missing intent/tasks")
            
            # Normalize: ensure every task has action and keywords fields
            for task in result["tasks"]:
                task.setdefault("action", "CHAT")
                task.setdefault("keywords", [])
                task.setdefault("refined_query", user_input)
            
            return result

        except Exception as e:
            print(f"Router Error: {e}")
            return {
                "tasks": [{
                    "intent": "GENERAL",
                    "action": "CHAT",
                    "keywords": [],
                    "refined_query": user_input,
                }],
                "reasoning": f"Routed to GENERAL due to parsing error: {str(e)}"
            }

