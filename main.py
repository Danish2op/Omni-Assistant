from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
import os
import traceback
from contextlib import asynccontextmanager
from app.core.database_v2 import SupabaseV2Client
from app.agents.v2_router import V2RouterAgent
from app.agents.v2_analyst import V2AnalystAgent
from app.agents.v2_archivist import V2ArchivistAgent
from app.agents.v2_organizer import V2OrganizerAgent
from app.agents.v2_general import V2GeneralAgent
from app.tools.news_api import scheduler, update_news_cache
from fastapi.middleware.cors import CORSMiddleware
from app.core.time_utils import format_ist_time

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and Shutdown logic for the Neural Hub."""
    print("Neural Hub: Starting background tasks...")
    scheduler.add_job(update_news_cache, 'interval', seconds=60)
    scheduler.start()
    await update_news_cache()
    yield
    print("Neural Hub: Shutting down scheduler...")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_client = SupabaseV2Client()
router_agent = V2RouterAgent()
analyst_agent = V2AnalystAgent()
archivist_agent = V2ArchivistAgent()
organizer_agent = V2OrganizerAgent()
general_agent = V2GeneralAgent()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {
        "status": "Omni-Agent V2 Neural Hub Online",
        "message": "Welcome to the future of cognitive assistance.",
        "version": "2.0.0--COGNITIVE",
        "standard": "IST (Asia/Kolkata)",
        "endpoints": ["/health", "/chat", "/tasks", "/knowledge", "/api/briefing"]
    }

@app.get("/health")
def health_check():
    return {"status": "Omni-Assistant Online", "version": "3.0.0-COGNITIVE"}


# ---- DATA ENDPOINTS (Frontend reads through these, NOT direct Supabase) ----

class TaskUpdateRequest(BaseModel):
    task_id: str
    status: str


@app.get("/tasks")
def list_tasks():
    """Return all tasks ordered by status and due_date."""
    try:
        records = db_client.get_data('tasks', {"limit": 200})
        # Sort: pending first, then by due_date
        if records:
            records.sort(key=lambda t: (
                0 if t.get('status') == 'pending' else 1,
                t.get('due_date') or '9999-12-31'
            ))
        return {"tasks": records or []}
    except Exception as e:
        print(f"Tasks List Error: {e}")
        return {"tasks": [], "error": str(e)}


@app.get("/knowledge")
def list_knowledge():
    """Return all knowledge base entries, newest first. (Fallback for v1 compatibility)"""
    try:
        records = db_client.get_data('knowledge_base', {"limit": 200})
        if records:
            records.sort(key=lambda k: k.get('created_at', ''), reverse=True)
        return {"knowledge": records or []}
    except Exception as e:
        print(f"Knowledge List Error: {e}")
        return {"knowledge": [], "error": str(e)}

@app.get("/v2/memories")
def list_v2_memories():
    """Return all V2 memories, newest first."""
    try:
        records = db_client.get_data('v2_memories', {"limit": 200})
        if records:
            records.sort(key=lambda k: k.get('created_at', ''), reverse=True)
        return {"memories": records or []}
    except Exception as e:
        print(f"V2 Memories List Error: {e}")
        return {"memories": [], "error": str(e)}


@app.patch("/tasks/update")
def update_task_status(request: TaskUpdateRequest):
    """Toggle a task's status between pending/completed."""
    try:
        result = db_client.update_data(
            "tasks",
            {"id": request.task_id},
            {"status": request.status}
        )
        if result:
            return {"status": "success", "updated": result}
        else:
            return {"status": "error", "message": "Task not found or database unavailable."}
    except Exception as e:
        print(f"Task Update Error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/briefing")
def get_briefing():
    """Return a lightweight daily briefing with task counts and recent knowledge."""
    try:
        tasks = db_client.get_data('tasks', {"limit": 200}) or []
        knowledge = db_client.get_data('knowledge_base', {"limit": 5}) or []

        pending = [t for t in tasks if t.get('status') == 'pending']
        completed = [t for t in tasks if t.get('status') == 'completed']

        return {
            "status": "success",
            "briefing": {
                "total_tasks": len(tasks),
                "pending_tasks": len(pending),
                "completed_tasks": len(completed),
                "upcoming": pending[:5],
                "recent_knowledge": knowledge[:5],
            }
        }
    except Exception as e:
        print(f"Briefing Error: {e}")
        return {"status": "error", "briefing": None, "message": str(e)}

@app.post("/chat")
def chat(request: ChatRequest):
    """
    Cognitive Orchestrator with action-aware dispatch and graceful error recovery.
    """
    try:
        # Step 1: Router generates an Execution Plan
        route_result = router_agent.route_request(request.message)
        tasks = route_result.get("tasks", [])
        
        execution_log = []
        shared_context = ""
        
        # Step 2: Sequential Execution
        for i, task in enumerate(tasks):
            intent = task.get("intent", "GENERAL")
            action = task.get("action", "CHAT")
            keywords = task.get("keywords", [])
            refined_query = task.get("refined_query", request.message)
            
            # CLARIFY handler: respond immediately without dispatching
            if action == "CLARIFY":
                return {
                    "status": "Completed",
                    "intent": "GENERAL",
                    "response": "I need a bit more context to help you. Could you rephrase your request or be more specific about what you'd like me to do?"
                }
            
            # Prepare query with injected context from previous step
            agent_query = refined_query
            if shared_context:
                agent_query = f"{refined_query}\n\n[CONTEXT_FROM_PREVIOUS_STEP]: {shared_context}"
            
            try:
                response = ""
                if intent == "ANALYST":
                    response = analyst_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ARCHIVIST":
                    response = archivist_agent.handle_query(
                        request.message, action=action, keywords=keywords, processed_query=agent_query
                    )
                elif intent == "ORGANIZER":
                    response = organizer_agent.handle_query(
                        request.message, action=action, keywords=keywords, processed_query=agent_query
                    )
                else:
                    response = general_agent.handle_query(request.message, processed_query=agent_query)

                # Defense: Ensure response is never None/empty
                response = response if response else "I processed your request but didn't get a clear result."

                execution_log.append({"intent": intent, "response": response})
                
                # Pass context to next step
                if i < len(tasks) - 1:
                    shared_context = response[:2000]

            except Exception as agent_err:
                # Log the real error server-side
                print(f"Agent Execution Failure ({intent}): {traceback.format_exc()}")
                # Return user-friendly message — no technical details
                agent_names = {
                    "ANALYST": "News & Markets",
                    "ARCHIVIST": "Memory",
                    "ORGANIZER": "Task Manager",
                    "GENERAL": "General Assistant"
                }
                friendly_name = agent_names.get(intent, intent)
                return {
                    "status": "Completed",
                    "intent": intent,
                    "response": f"I encountered a technical glitch while accessing the {friendly_name}. I'm still online — could you try rephrasing that or asking something else?"
                }

        # Step 3: Final Response
        if not execution_log:
            return {"status": "Completed", "response": "I processed your request but no actions were taken."}
            
        if len(execution_log) == 1:
            return {
                "status": "Completed",
                "intent": execution_log[0]["intent"],
                "response": execution_log[0]["response"]
            }
        else:
            final_summary = general_agent.synthesize_final_response(request.message, execution_log)
            return {
                "status": "Completed",
                "intent": "ORCHESTRATOR",
                "response": final_summary if final_summary else "I completed multiple steps but couldn't synthesize a final summary."
            }

    except Exception as global_err:
        print(f"CRITICAL GLOBAL ERROR: {traceback.format_exc()}")
        return {
            "status": "Completed",
            "intent": "SYSTEM_FAILSAFE",
            "response": "I encountered an unexpected issue. I'm still online — could you try again or rephrase your request?"
        }

