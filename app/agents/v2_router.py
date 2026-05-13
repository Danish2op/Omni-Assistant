"""
V2 Orchestrator Router — Multi-Model Intent Classifier.

Uses verified free-tier models (primary: Gemma-4) for fast intent classification.
Routes to specialized sub-agents: CODER, RESEARCHER, ANALYST, ARCHIVIST, ORGANIZER, COMMUNICATOR, GENERAL.
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
    confidence: float = Field(default=1.0, description="0.0 to 1.0 confidence in this classification")


class ExecutionPlan(BaseModel):
    """Router output — validated execution plan."""
    tasks: List[TaskPlan]
    reasoning: str = ""


# ---- System Prompt ----

V2_ROUTER_SYSTEM_PROMPT = """You are the Orchestrator for Omni-Agent V2. Your goal is to decompose user input into a precise Execution Plan.

STRICT OUTPUT RULE: Output ONLY valid JSON. No markdown, no preamble, no explanation.

INTENT + ACTION VOCABULARY:
- ORGANIZER: CREATE, LIST, FILTER, UPDATE (task management)
- ARCHIVIST: STORE, RETRIEVE (memory, credentials, notes, knowledge base)
- ANALYST: RESEARCH (news, markets, web search, current events)
- CODER: CODE (technical implementation, writing/debugging functions, explaining code logic)
- RESEARCHER: DEEP_RESEARCH (complex synthesis, multi-step deep dives)
- COMMUNICATOR: EMAIL, REMIND, SCHEDULE (external communication or temporal triggers)
- GENERAL: CHAT, CLARIFY (meta-talk, greetings, ambiguous requests)

--- COGNITIVE HARDENING RULES ---

1. ARCHIVIST vs CODER (The "Credential Rule"):
   - If user says "Remember", "Store", "Save", "Keep note of" followed by technical info (SSH, API keys, IPs, passwords) → ARCHIVIST/STORE.
   - If user asks "How do I SSH", "Write a script for X", "Debug this code" → CODER/CODE.
   - NEVER route "Remember my [credential]" to CODER.
   - EXCEPTION: If the user says "remember" regarding logic, syntax, or code patterns (e.g., "remember to add a try-catch", "remember how we wrote that loop"), route to CODER.

2. CONTEXT RESET (The "Fresh Start Rule"):
   - If the User Input starts with "Anyway", "Also", "By the way", "New task", or "Now", treat it as a POTENTIAL context reset.
   - If User Input is semantically unrelated to the last message in History, IGNORE the history for classification.

3. CONTEXT FOLLOW-UP (The "Greed Rule"):
   - ONLY reconstruct a task (Contextual Follow-up) if the User Input is EXCLUSIVELY providing info requested in the History (e.g., just an email, a name, or a confirmation).
   - If the User Input contains a new verb or command, treat it as a NEW task.

4. MULTI-INTENT DECOMPOSITION:
   - If the user says "Email Paryag and also remember my password", create TWO tasks: COMMUNICATOR/EMAIL and ARCHIVIST/STORE.

5. AMBIGUITY & CONFIDENCE (The "Clarify Rule"):
   - If you are less than 70% sure of the intent, set action="CLARIFY" and intent="GENERAL".
   - Reasoning must include a brief chain-of-thought.

6. COMMUNICATOR ACTION RULE:
   - EMAIL: One-off request to send an email immediately.
   - REMIND: One-off request to be reminded at a specific time/delay.
   - SCHEDULE: Any request containing "every day", "weekly", "routine", "recurring", "daily", or specifying a recurring timeframe.

--- ROUTING LOGIC EXAMPLES ---

User: "ssh root@65.109.150.223 pw: 1234. mail it to me"
History: [User asked about something else]
{
  "tasks": [
    {"intent": "ARCHIVIST", "action": "STORE", "keywords": ["ssh", "credentials"], "refined_query": "Store SSH credentials for 65.109.150.223"},
    {"intent": "COMMUNICATOR", "action": "EMAIL", "keywords": ["ssh", "credentials"], "refined_query": "Email the SSH credentials to the user"}
  ],
  "reasoning": "User wants to store and also email the credentials."
}

User: "paryag.sahni@thefuture.university"
History: [Agent: "What is the email id?"]
{
  "tasks": [{"intent": "COMMUNICATOR", "action": "EMAIL", "keywords": [], "refined_query": "Resume email task: Send to paryag.sahni@thefuture.university"}],
  "reasoning": "Pure follow-up info provided."
}

User: "Anyway, write a python function to scrape a site"
History: [Previous talk about Paryag]
{
  "tasks": [{"intent": "CODER", "action": "CODE", "keywords": ["python", "scrape"], "refined_query": "Write a python function for web scraping"}],
  "reasoning": "User used 'Anyway' to signal a new task, disregarding Paryag context."
}

User: "Remember where I kept my car keys"
{
  "tasks": [{"intent": "ARCHIVIST", "action": "STORE", "keywords": ["car keys"], "refined_query": "Store memory: Car keys location"}],
  "reasoning": "Memory storage."
}

User: "set a routine every day to email me motivational quotes at 8 AM"
{
  "tasks": [{"intent": "COMMUNICATOR", "action": "SCHEDULE", "keywords": ["routine", "quotes"], "refined_query": "Set a daily routine to email motivational quotes at 8 AM"}],
  "reasoning": "User specified 'routine' and 'every day', triggering a recurring schedule."
}
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
