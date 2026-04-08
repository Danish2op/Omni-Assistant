from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
import os
from app.core.database import SupabaseClient
from app.agents.router import RouterAgent
from app.agents.analyst import AnalystAgent
from app.agents.archivist import ArchivistAgent
from app.agents.organizer import OrganizerAgent
from app.agents.general import GeneralAgent
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

app = FastAPI()

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

class TaskUpdateRequest(BaseModel):
    task_id: str
    status: str


@app.get("/health")
def health_check():
    return {"status": "Omni-Assistant Online", "version": "2.0.0"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        # Step 1: Decompose query into a sequence of tasks
        route_result = router_agent.route_request(request.message)
        tasks = route_result.get("tasks", [])
        
        execution_log = []
        shared_context = ""
        
        # Step 2: Sequential Execution with Circuit Breaker
        for task in tasks:
            intent = task.get("intent")
            refined_query = task.get("refined_query", request.message)
            
            # Prepare query (inject context if it's a chained task)
            agent_query = refined_query
            if shared_context:
                agent_query = f"{refined_query}\n\n[CONTEXT FROM PREVIOUS STEP]: {shared_context}"
            
            try:
                # Dispatch
                if intent == "ANALYST":
                    response = analyst_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ARCHIVIST":
                    response = archivist_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "ORGANIZER":
                    response = organizer_agent.handle_query(request.message, processed_query=agent_query)
                elif intent == "GENERAL":
                    response = general_agent.handle_query(request.message, processed_query=agent_query)
                else:
                    raise ValueError(f"Unknown intent: {intent}")

                # Circuit Breaker: Check for obvious failures
                if "error" in response.lower() or "couldn't find" in response.lower():
                     return {
                        "status": "Circuit Breaker Triggered",
                        "intent": intent,
                        "response": f"I encountered a problem during the {intent} phase: {response}. I've stopped the sequence to prevent incorrect actions."
                    }

                # Success: Store in log and update shared_context
                execution_log.append({
                    "intent": intent,
                    "response": response
                })
                
                # Summarize for next step (Context Summarization constraint)
                shared_context = general_agent.summarize_context(response)

            except Exception as e:
                return {
                    "status": "Failure",
                    "intent": intent,
                    "response": f"I encountered a technical error in the {intent} step: {str(e)}. Execution halted."
                }

        # Step 3: Final Synthesis (Unified Summary constraint)
        if not execution_log:
            return {"status": "No Tasks", "response": "I couldn't determine any actions to take."}
            
        if len(execution_log) == 1:
            # Backward Compatibility: Return direct result if single-intent
            return {
                "status": "Completed",
                "intent": execution_log[0]["intent"],
                "response": execution_log[0]["response"]
            }
        else:
            # Multi-intent: Synthesize into one unified message
            final_summary = general_agent.synthesize_final_response(request.message, execution_log)
            return {
                "status": "Sequence Completed",
                "intents": [t["intent"] for t in execution_log],
                "response": final_summary,
                "detail_log": execution_log
            }

    except Exception as e:
        return {"status": "Error", "error": str(e)}
