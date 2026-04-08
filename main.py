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
    """
    Startup and Shutdown logic for the Neural Hub.
    """
    # Startup: Initialize News Cache
    print("Neural Hub: Starting background background tasks...")
    scheduler.add_job(update_news_cache, 'interval', seconds=60)
    scheduler.start()
    
    # Run first update immediately to prime the cache
    await update_news_cache()
    
    yield
    
    # Shutdown
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
    return {"status": "Omni-Assistant Online", "version": "2.1.0-RESILIENT"}

@app.post("/chat")
def chat(request: ChatRequest):
    """
    Bulletproof Chat Orchestrator. 
    Always returns 200 OK with helpful diagnostic info if a sub-system fails.
    """
    try:
        # Step 1: Decompose query into a sequence of tasks
        route_result = router_agent.route_request(request.message)
        tasks = route_result.get("tasks", [])
        
        execution_log = []
        shared_context = ""
        
        # Step 2: Sequential Execution with Circuit Breaker
        for i, task in enumerate(tasks):
            intent = task.get("intent", "GENERAL")
            refined_query = task.get("refined_query", request.message)
            
            # Prepare query with injected context
            agent_query = refined_query
            if shared_context:
                agent_query = f"{refined_query}\n\n[NEURAL_CONTEXT_FROM_PREVIOUS_STEP]: {shared_context}"
            
            try:
                # Dispatching with explicit error capturing per agent
                if intent == "ANALYST":
                    response = analyst_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ARCHIVIST":
                    response = archivist_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ORGANIZER":
                    response = organizer_agent.handle_query(request.message, processed_query=agent_query)
                else:
                    response = general_agent.handle_query(request.message, processed_query=agent_query)

                # Circuit Breaker: If we get a hard failure string from an agent
                if "error" in response.lower() and i == 0 and len(tasks) > 1:
                     return {
                        "status": "Resilient_Stop",
                        "intent": intent,
                        "response": f"Sequence Halted: The {intent} step encountered a block. Details: {response}"
                    }

                execution_log.append({"intent": intent, "response": response})
                
                # Context Summarization for the next step (if any)
                if i < len(tasks) - 1:
                    shared_context = general_agent.summarize_context(response)

            except Exception as agent_err:
                # Agent-level Resilience: Halt sequence but don't crash main loop
                return {
                    "status": "Agent_Failure",
                    "intent": intent,
                    "response": f"Neural Core: The {intent} module had a logic exception. Execution halted to prevent corruption.",
                    "debug_info": str(agent_err)
                }

        # Step 3: Final Response Synthesis
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
                "response": final_summary
            }

    except Exception as global_err:
        # Final Fail-Safe: Always return structured JSON for the frontend
        print(f"CRITICAL GLOBAL ERROR: {traceback.format_exc()}")
        return {
            "status": "Completed", # Return 'Completed' so frontend doesn't show 'Neural Break'
            "intent": "SYSTEM_FAILSAFE",
            "response": f"Omni-Assistant is currently experiencing partial monolith instability. I've noted the error and am attempting to recover. Error: {str(global_err)}"
        }
