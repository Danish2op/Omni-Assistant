from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
import os
import traceback
from contextlib import asynccontextmanager
from app.core.database import SupabaseClient
from app.agents.router import RouterAgent
from app.agents.analyst import AnalystAgent
from app.agents.archivist import ArchivistAgent
from app.agents.organizer import OrganizerAgent
from app.agents.general import GeneralAgent
from app.tools.news_api import scheduler, update_news_cache
from fastapi.middleware.cors import CORSMiddleware

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

db_client = SupabaseClient()
router_agent = RouterAgent()
analyst_agent = AnalystAgent()
archivist_agent = ArchivistAgent()
organizer_agent = OrganizerAgent()
general_agent = GeneralAgent()


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health_check():
    return {"status": "Omni-Assistant Online", "version": "3.0.0-COGNITIVE"}

@app.get("/api/briefing")
def get_briefing():
    """
    Daily Briefing Backend Engine
    Gather pending tasks and top news, synthesize a short morning briefing.
    """
    fallback = "Welcome to Omni-Assistant. All systems are operational."
    try:
        # Get pending tasks
        tasks = db_client.client.table("tasks").select("*").eq("status", "pending").execute().data or []
        tasks_text = "\n".join([f"- {t.get('title', 'Unknown Task')}" for t in tasks]) if tasks else "No pending tasks."

        # Get top 3 news items
        from app.tools.news_api import NewsTool
        news_items = NewsTool().fetch_latest_news(limit=3)
        news_text = "\n".join([f"- {n.get('title', '')}: {n.get('summary', '')}" for n in news_items]) if news_items else "No current news."

        # Synthesize using Gemini
        from app.core.llm import GeminiClient
        prompt = (
            f"Here are the user's current pending tasks:\n{tasks_text}\n\n"
            f"Here are the top news headlines right now:\n{news_text}\n\n"
            "Synthesize a 2-3 sentence morning briefing connecting these active tasks to the current news if explicitly relevant. Do not hallucinate."
        )
        briefing = GeminiClient().generate_response(prompt=prompt, system_instruction="You are a helpful and concise AI assistant.")
        if not briefing:
            return {"briefing": fallback}
        return {"briefing": briefing}

    except Exception as e:
        print(f"Briefing Endpoint Error: {e}")
        return {"briefing": fallback}

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

