"""
Omni-Agent V2 — Multi-Model Orchestrated Backend.

Entry point for the V2 architecture. Uses:
- V2 Router (Gemma-4 intent classification)
- V2 Sub-Agents (each with role-specific model cascades)
- V2 Database (graceful Supabase pause detection)
- Keep-alive cron (GitHub Actions)

Runs alongside V1 main.py — same FastAPI patterns, different pipeline.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from pydantic import BaseModel
import traceback
import json as json_mod
from contextlib import asynccontextmanager
from app.core.database_v2 import SupabaseV2Client
from app.agents.v2_router import V2RouterAgent
from app.agents.v2_analyst import V2AnalystAgent
from app.agents.v2_archivist import V2ArchivistAgent
from app.agents.v2_organizer import V2OrganizerAgent
from app.agents.v2_general import V2GeneralAgent
from app.core.llm_v2 import MultiModelClient, AgentRole
from app.tools.news_api import scheduler, update_news_cache
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and Shutdown logic for V2 Neural Hub."""
    print("🧠 Omni-Agent V2: Starting...")
    scheduler.add_job(update_news_cache, "interval", seconds=60)
    scheduler.start()
    await update_news_cache()
    yield
    print("🧠 Omni-Agent V2: Shutting down...")
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- V2 Agent Instances ----
db_client = SupabaseV2Client()
router_agent = V2RouterAgent()
analyst_agent = V2AnalystAgent()
archivist_agent = V2ArchivistAgent()
organizer_agent = V2OrganizerAgent()
general_agent = V2GeneralAgent()
coder_llm = MultiModelClient()  # Direct LLM for CODER/RESEARCHER roles


class ChatRequest(BaseModel):
    message: str


class TaskUpdateRequest(BaseModel):
    task_id: str
    status: str


# ---- Info Endpoints ----

@app.get("/")
def root():
    return {
        "status": "Omni-Agent V2 Online",
        "version": "2.0.0-MULTI-MODEL",
        "architecture": {
            "router": "Gemma-4 Intent Classifier",
            "models": "Multi-model with fallback cascades",
            "agents": ["ANALYST", "ARCHIVIST", "ORGANIZER", "CODER", "RESEARCHER", "GENERAL"],
        },
        "endpoints": ["/health", "/chat", "/chat/stream", "/tasks", "/knowledge", "/v2/memories", "/api/briefing"],
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0-MULTI-MODEL"}


# ---- Data Endpoints ----

@app.get("/tasks")
def list_tasks():
    try:
        records = db_client.get_data("tasks", {"limit": 200})
        if records is None:
            return {"tasks": [], "warning": "Database may be paused. Check Supabase."}
        if records:
            records.sort(
                key=lambda t: (
                    0 if t.get("status") == "pending" else 1,
                    t.get("due_date") or "9999-12-31",
                )
            )
        return {"tasks": records or []}
    except Exception as e:
        print(f"[V2] Tasks List Error: {e}")
        return {"tasks": [], "error": str(e)}


@app.get("/knowledge")
def list_knowledge():
    try:
        records = db_client.get_data("knowledge_base", {"limit": 200})
        if records is None:
            return {"knowledge": [], "warning": "Database may be paused."}
        if records:
            records.sort(key=lambda k: k.get("created_at", ""), reverse=True)
        return {"knowledge": records or []}
    except Exception as e:
        print(f"[V2] Knowledge List Error: {e}")
        return {"knowledge": [], "error": str(e)}


@app.get("/v2/memories")
def list_v2_memories():
    """V2-specific: Return metadata-tagged memories."""
    try:
        records = db_client.get_data("v2_memories", {"limit": 100})
        if records is None:
            return {"memories": [], "warning": "Database may be paused."}
        return {"memories": records or []}
    except Exception as e:
        print(f"[V2] Memories List Error: {e}")
        return {"memories": [], "error": str(e)}


@app.patch("/tasks/update")
def update_task_status(request: TaskUpdateRequest):
    try:
        result = db_client.update_data("tasks", {"id": request.task_id}, {"status": request.status})
        if result is None:
            return {"status": "error", "message": "Database may be paused."}
        if result:
            return {"status": "success", "updated": result}
        return {"status": "error", "message": "Task not found."}
    except Exception as e:
        print(f"[V2] Task Update Error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/briefing")
def get_briefing():
    try:
        tasks = db_client.get_data("tasks", {"limit": 200}) or []
        knowledge = db_client.get_data("knowledge_base", {"limit": 5}) or []
        v2_memories = db_client.get_data("v2_memories", {"limit": 5}) or []

        pending = [t for t in tasks if t.get("status") == "pending"]
        completed = [t for t in tasks if t.get("status") == "completed"]

        return {
            "status": "success",
            "briefing": {
                "total_tasks": len(tasks),
                "pending_tasks": len(pending),
                "completed_tasks": len(completed),
                "upcoming": pending[:5],
                "recent_knowledge": knowledge[:5],
                "recent_v2_memories": v2_memories[:3],
            },
        }
    except Exception as e:
        print(f"[V2] Briefing Error: {e}")
        return {"status": "error", "briefing": None, "message": str(e)}


# ---- V2 Chat: Multi-Model Orchestrated Pipeline ----

CODER_SYSTEM_PROMPT = """You are the Coder for Omni-Agent V2. You write clean, production-grade code.

RULES:
- Direct code first, explanation after.
- Include language identifier in code fences.
- Handle edge cases.
- If debugging, identify root cause before suggesting fixes."""

RESEARCHER_SYSTEM_PROMPT = """You are the Deep Researcher for Omni-Agent V2. You perform multi-step research with reasoning.

RULES:
- Break complex questions into sub-questions.
- Synthesize from multiple angles.
- State confidence level for each claim.
- Cite reasoning chain explicitly."""


@app.post("/chat")
def chat(request: ChatRequest):
    """
    V2 Cognitive Orchestrator:
    Router → Intent Classification → Agent Dispatch → Synthesize
    """
    try:
        # Step 1: V2 Router classifies intent
        route_result = router_agent.route_request(request.message)
        tasks = route_result.get("tasks", [])

        execution_log = []
        shared_context = ""

        # Step 2: Sequential execution with context passing
        for i, task in enumerate(tasks):
            intent = task.get("intent", "GENERAL")
            action = task.get("action", "CHAT")
            keywords = task.get("keywords", [])
            refined_query = task.get("refined_query", request.message)

            # CLARIFY → route through GENERAL agent for a real response
            if action == "CLARIFY":
                intent = "GENERAL"

            # Inject context from previous step
            agent_query = refined_query
            if shared_context:
                agent_query = f"{refined_query}\n\n[CONTEXT_FROM_PREVIOUS_STEP]: {shared_context}"

            try:
                response = _dispatch_agent(
                    intent, action, keywords, request.message, agent_query
                )
                response = response or "I processed your request but didn't get a clear result."
                execution_log.append({"intent": intent, "response": response})

                # Pass context to next step
                if i < len(tasks) - 1:
                    shared_context = response[:2000]

            except Exception as agent_err:
                print(f"[V2] Agent Failure ({intent}): {traceback.format_exc()}")
                agent_names = {
                    "ANALYST": "Research & News",
                    "ARCHIVIST": "Memory",
                    "ORGANIZER": "Task Manager",
                    "CODER": "Code Assistant",
                    "RESEARCHER": "Deep Research",
                    "GENERAL": "General Assistant",
                }
                friendly_name = agent_names.get(intent, intent)
                return {
                    "status": "Completed",
                    "intent": intent,
                    "response": f"I hit a glitch with the {friendly_name}. I'm still online — try rephrasing?",
                }

        # Step 3: Final response
        if not execution_log:
            return {"status": "Completed", "response": "No actions taken."}

        if len(execution_log) == 1:
            return {
                "status": "Completed",
                "intent": execution_log[0]["intent"],
                "response": execution_log[0]["response"],
            }
        else:
            final_summary = general_agent.synthesize_final_response(
                request.message, execution_log
            )
            return {
                "status": "Completed",
                "intent": "ORCHESTRATOR",
                "response": final_summary or "Completed multiple steps but couldn't synthesize.",
            }

    except Exception as global_err:
        print(f"[V2] CRITICAL ERROR: {traceback.format_exc()}")
        return {
            "status": "Completed",
            "intent": "SYSTEM_FAILSAFE",
            "response": "I encountered an unexpected issue. Try again or rephrase?",
        }


# ---- V2 SSE Streaming Chat ----

def _sse_event(event_type: str, **kwargs) -> str:
    """Format SSE event: data: {json}\n\n"""
    payload = {"type": event_type, **kwargs}
    return f"data: {json_mod.dumps(payload)}\n\n"


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    """
    SSE streaming version of /chat.
    Events: ROUTER → AGENT → TEXT (chunks) → DONE
    """
    def event_generator():
        try:
            # Step 1: Route
            route_result = router_agent.route_request(request.message)
            tasks = route_result.get("tasks", [])

            if not tasks:
                yield _sse_event("ROUTER", intent="GENERAL")
                yield _sse_event("TEXT", content="No actions identified.")
                yield "data: [DONE]\n\n"
                return

            task = tasks[0]
            intent = task.get("intent", "GENERAL")
            action = task.get("action", "CHAT")
            refined_query = task.get("refined_query", request.message)
            keywords = task.get("keywords", [])

            if action == "CLARIFY":
                intent = "GENERAL"

            yield _sse_event("ROUTER", intent=intent)

            # Step 2: Agent dispatch
            agent_names = {
                "ANALYST": "Research & News",
                "ARCHIVIST": "Memory",
                "ORGANIZER": "Task Manager",
                "CODER": "Code Assistant",
                "RESEARCHER": "Deep Research",
                "GENERAL": "General Assistant",
            }
            yield _sse_event("AGENT", name=agent_names.get(intent, intent))

            # Step 3: Stream or non-stream based on agent
            if intent in ("CODER", "RESEARCHER"):
                # These support token streaming
                sys_prompt = CODER_SYSTEM_PROMPT if intent == "CODER" else RESEARCHER_SYSTEM_PROMPT
                role = AgentRole.CODER if intent == "CODER" else AgentRole.RESEARCHER

                for chunk in coder_llm.generate_stream(
                    prompt=refined_query,
                    system_instruction=sys_prompt,
                    role=role,
                    max_tokens=4096,
                    temperature=0.4 if intent == "CODER" else 0.6,
                ):
                    yield _sse_event("TEXT", content=chunk)
            else:
                # Non-streamable agents — get full response, emit as one TEXT
                response = _dispatch_agent(intent, action, keywords, request.message, refined_query)
                response = response or "Processed but no clear result."
                yield _sse_event("TEXT", content=response)

            yield "data: [DONE]\n\n"

        except Exception as e:
            print(f"[V2 STREAM] Error: {traceback.format_exc()}")
            yield _sse_event("ERROR", message="Stream interrupted. Try again.")
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _dispatch_agent(
    intent: str, action: str, keywords: list, raw_input: str, agent_query: str
) -> str:
    """Route to the correct V2 agent based on intent."""

    if intent == "ANALYST":
        return analyst_agent.handle_query(raw_input, processed_query=agent_query)

    elif intent == "ARCHIVIST":
        return archivist_agent.handle_query(
            raw_input, action=action, keywords=keywords, processed_query=agent_query
        )

    elif intent == "ORGANIZER":
        return organizer_agent.handle_query(
            raw_input, action=action, keywords=keywords, processed_query=agent_query
        )

    elif intent == "CODER":
        return coder_llm.generate(
            prompt=agent_query,
            system_instruction=CODER_SYSTEM_PROMPT,
            role=AgentRole.CODER,
            max_tokens=4096,
            temperature=0.4,
        )

    elif intent == "RESEARCHER":
        return coder_llm.generate(
            prompt=agent_query,
            system_instruction=RESEARCHER_SYSTEM_PROMPT,
            role=AgentRole.RESEARCHER,
            max_tokens=4096,
            temperature=0.6,
        )

    else:
        return general_agent.handle_query(raw_input, processed_query=agent_query)
