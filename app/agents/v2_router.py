"""
V2 Orchestrator Router — Multi-Model Intent Classifier.

Uses Gemma-4 (ORCHESTRATOR role) for fast intent classification.
Routes to specialized sub-agents: CODER, RESEARCHER, ANALYST, ARCHIVIST, ORGANIZER, GENERAL.
Outputs are Pydantic-validated for deterministic routing.
"""

import json
from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.llm_v2 import MultiModelClient, AgentRole


# ---- Pydantic Models for Deterministic Output ----

class TaskPlan(BaseModel):
    """Single task in the execution plan."""
    intent: str = Field(
        ...,
        description="Target agent: ANALYST, ARCHIVIST, ORGANIZER, CODER, RESEARCHER, COMMUNICATOR, GENERAL"
    )
    action: str = Field(
        default="CHAT",
        description="Action verb: CREATE, LIST, FILTER, UPDATE, STORE, RETRIEVE, RESEARCH, CODE, CHAT, CLARIFY"
    )
    keywords: List[str] = Field(default_factory=list)
    refined_query: str = Field(default="")


class ExecutionPlan(BaseModel):
    """Router output — validated execution plan."""
    tasks: List[TaskPlan]
    reasoning: str = ""


# ---- System Prompt ----

V2_ROUTER_SYSTEM_PROMPT = """You are the Orchestrator for Omni-Agent V2. Decompose user input into an Execution Plan.

STRICT OUTPUT RULE: Output ONLY valid JSON. No markdown, no preamble, no explanation.

INTENT + ACTION VOCABULARY:
- ORGANIZER: CREATE, LIST, FILTER, UPDATE (task management)
- ARCHIVIST: STORE, RETRIEVE (memory/knowledge base)
- ANALYST: RESEARCH (news, markets, web search, general info lookup)
- CODER: CODE (write code, debug, explain code, technical implementation)
- RESEARCHER: DEEP_RESEARCH (complex multi-step research requiring reasoning and synthesis)
- COMMUNICATOR: EMAIL, REMIND, SCHEDULE (sending emails, scheduling routines/reminders)
- GENERAL: CHAT, CLARIFY (greetings, meta-questions, ambiguous input)

ROUTING RULES:
- Simple code questions or "write me a function" → CODER/CODE
- "Research X deeply", "compare A vs B", "analyze the pros and cons" → RESEARCHER/DEEP_RESEARCH
- "Latest news on X", "what happened with Y", weather, market data → ANALYST/RESEARCH
- Task CRUD operations → ORGANIZER
- Memory save/recall or "what did I say about X" → ARCHIVIST/RETRIEVE or ARCHIVIST/STORE
- "Send an email to X", "remind me to Y at 9pm", "set up a daily news email" → COMMUNICATOR
- Greetings, vague input → GENERAL/CHAT or GENERAL/CLARIFY
- MULTI-INTENT REQUESTS: If the user asks for two or more distinct things (e.g., "search for X and save Y"), decompose them into a LIST of tasks. DO NOT combine them into one.
- CONTEXTUAL FOLLOW-UPS: If the user provides information (like an email address, contact name, or specific detail) that was previously requested by an agent or is a clear continuation of a previous task, ROUTE it back to the agent that needed it. CRITICAL: In the 'refined_query', reconstruct the FULL task using the new info (e.g., if user provides an email, the refined_query should be 'Send the email to [email] with the original intent').

OUTPUT FORMAT:
{"tasks": [{"intent": "ANALYST", "action": "RESEARCH", "keywords": ["SpaceX"], "refined_query": "Search latest SpaceX news"}], "reasoning": "User wants news"}

EXAMPLES:

User: "paryag.sahni@thefuture.university" (History: AI asked "What is Paryag's email?")
{"tasks": [{"intent": "COMMUNICATOR", "action": "EMAIL", "keywords": ["paryag.sahni@thefuture.university"], "refined_query": "Send email to Paryag at paryag.sahni@thefuture.university reminding him to work hard"}], "reasoning": "User provided requested email; resuming original email task."}

User: "What's the weather in Tokyo and add a task to book flights"
{"tasks": [
    {"intent": "ANALYST", "action": "RESEARCH", "keywords": ["weather", "Tokyo"], "refined_query": "Current weather in Tokyo"},
    {"intent": "ORGANIZER", "action": "CREATE", "keywords": ["flights"], "refined_query": "Create task: Book flights to Tokyo"}
], "reasoning": "Weather lookup + task creation"}

User: "Check the weather in Punjab then remind me where my key is"
{"tasks": [
    {"intent": "ANALYST", "action": "RESEARCH", "keywords": ["weather", "Punjab"], "refined_query": "Current weather in Punjab, India"},
    {"intent": "ARCHIVIST", "action": "RETRIEVE", "keywords": ["key"], "refined_query": "Where is my key stored?"}
], "reasoning": "Decomposed into web search and memory retrieval"}

User: "Write a Python function to sort a list"
{"tasks": [{"intent": "CODER", "action": "CODE", "keywords": ["python", "sort", "list"], "refined_query": "Write a Python function to sort a list"}], "reasoning": "Code generation request"}

User: "What's the latest on OpenAI?"
{"tasks": [{"intent": "ANALYST", "action": "RESEARCH", "keywords": ["OpenAI", "latest"], "refined_query": "Search latest OpenAI news and updates"}], "reasoning": "News lookup"}

User: "Add a task to review pull requests"
{"tasks": [{"intent": "ORGANIZER", "action": "CREATE", "keywords": [], "refined_query": "Create task: Review pull requests"}], "reasoning": "Task creation"}

User: "Remember my API key is stored in Vault"
{"tasks": [{"intent": "ARCHIVIST", "action": "STORE", "keywords": [], "refined_query": "Store: API key is stored in Vault"}], "reasoning": "Memory storage"}

User: "Hello"
{"tasks": [{"intent": "GENERAL", "action": "CHAT", "keywords": [], "refined_query": "Respond to greeting"}], "reasoning": "Greeting"}
"""


class V2RouterAgent:
    """
    V2 Orchestrator: classifies intent using Gemma-4 and routes to
    specialized sub-agents via Pydantic-validated execution plans.
    """

    def __init__(self):
        self.llm = MultiModelClient()

    def route_request(self, user_input: str, history: List[dict] = None) -> dict:
        """
        Classify user intent and produce a validated execution plan.

        Returns dict with 'tasks' array, each task having:
        intent, action, keywords, refined_query.
        """
        try:
            from app.core.time_utils import format_ist_time
            current_time = format_ist_time()
            
            # Format history for the prompt
            history_str = ""
            if history:
                history_str = "Recent Conversation History:\n"
                for msg in history[-5:]: # Last 5 messages for context
                    role = msg.get("role", "user").upper()
                    content = msg.get("content", "")
                    history_str += f"{role}: {content}\n"
                history_str += "\n"

            prompt = f"Reference Time (IST): {current_time}\n\n{history_str}User Input: {user_input}"

            raw_response = self.llm.generate(
                prompt=prompt,
                system_instruction=V2_ROUTER_SYSTEM_PROMPT,
                role=AgentRole.ORCHESTRATOR,
                max_tokens=512,
                temperature=0.3,
            )

            # Clean JSON from LLM response
            cleaned = self._extract_json(raw_response)
            parsed = json.loads(cleaned)

            # Validate with Pydantic
            plan = ExecutionPlan(**parsed)
            return plan.model_dump()

        except json.JSONDecodeError as e:
            print(f"[V2 Router] JSON parse error: {e}")
            print(f"[V2 Router] Raw response: {raw_response[:200]}")
            return self._fallback_plan(user_input, f"JSON parse: {e}")

        except Exception as e:
            print(f"[V2 Router] Error: {e}")
            return self._fallback_plan(user_input, str(e))

    def _extract_json(self, raw: str) -> str:
        """Extract JSON object from potentially messy LLM output."""
        cleaned = raw.strip()

        # Strip markdown code fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0] if "\n" in cleaned else cleaned[:-3]

        # Find outermost JSON braces
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]

        return cleaned

    def _fallback_plan(self, user_input: str, error_msg: str) -> dict:
        """Return safe GENERAL/CHAT plan on any failure."""
        return ExecutionPlan(
            tasks=[TaskPlan(
                intent="GENERAL",
                action="CHAT",
                keywords=[],
                refined_query=user_input,
            )],
            reasoning=f"Fallback due to: {error_msg}"
        ).model_dump()
