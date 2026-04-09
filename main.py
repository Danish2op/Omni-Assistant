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
    print("Neural Hub: Starting background tasks...")
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
    return {"status": "Omni-Assistant Online", "version": "2.2.0-ULTRA-RESILIENT"}

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
                response = ""
                if intent == "ANALYST":
                    response = analyst_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ARCHIVIST":
                    response = archivist_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ORGANIZER":
                    # Pass the known sub-intent (CREATE/LIST/UPDATE) if available
                    response = organizer_agent.handle_query(request.message, pre_intent=intent, processed_query=agent_query)
                else:
                    response = general_agent.handle_query(request.message, processed_query=agent_query)

                # Defense: Ensure response is a valid string
                response = response if response else "Neural Core: Empty response received."

                # Circuit Breaker: If we get a hard failure string from an agent
                if "error" in response.lower() and i == 0 and len(tasks) > 1:
                     return {
                        "status": "Resilient_Stop",
                        "intent": intent,
                        "response": f"Sequence Halted: The {intent} step encountered a block. Details: {response}"
                    }

                execution_log.append({"intent": intent, "response": response})
                
                # OPTIMIZATION: Chain Collapse. Pass raw response to next agent directly.
                if i < len(tasks) - 1:
                    shared_context = response[:2000] # Truncate to avoid token bloat

            except Exception as agent_err:
                print(f"Agent Execution Failure: {traceback.format_exc()}")
                return {
                    "status": "Agent_Failure",
                    "intent": intent,
                    "response": f"Neural Core: The {intent} module had a logic exception. Execution halted.",
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
        print(f"CRITICAL GLOBAL ERROR: {traceback.format_exc()}")
        return {
            "status": "Completed",
            "intent": "SYSTEM_FAILSAFE",
            "response": f"Omni-Assistant is currently in survival mode. Error: {str(global_err)}"
        }
