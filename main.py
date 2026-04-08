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
    allow_origins=["*"],  # In production, we should specify the Vercel domain
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
    return {"status": "Omni-Assistant Online", "version": "1.0.0"}

@app.get("/test-db")
def test_db():
    try:
        response = db_client.get_data("knowledge_base", {"limit": 1})
        return {"status": "Database Connected", "data": response}
    except Exception as e:
        return {"status": "Database Connection Failed", "error": str(e)}

@app.patch("/tasks/update")
def update_task_status(request: TaskUpdateRequest):
    try:
        db_client.update_data("tasks", {"id": request.task_id}, {"status": request.status})
        return {"status": "Success", "message": f"Task {request.task_id} updated to {request.status}"}
    except Exception as e:
        return {"status": "Error", "error": str(e)}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        # Step 1: Route the request
        result = router_agent.route_request(request.message)
        intent = result.get("intent", "UNKNOWN")
        processed_query = result.get("processed_query", request.message)

        # Step 2: Dispatch to the appropriate sub-agent
        if intent == "ANALYST":
            answer = analyst_agent.handle_query(request.message, processed_query=processed_query)
            return {
                "status": "Completed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "response": answer
            }
        elif intent == "ARCHIVIST":
            answer = archivist_agent.handle_query(request.message, pre_intent=intent, processed_query=processed_query)
            return {
                "status": "Completed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "response": answer
            }
        elif intent == "ORGANIZER":
            answer = organizer_agent.handle_query(request.message, pre_intent=intent, processed_query=processed_query)
            return {
                "status": "Completed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "response": answer
            }
        elif intent == "GENERAL":
            answer = general_agent.handle_query(request.message, processed_query=processed_query)
            return {
                "status": "Completed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "response": answer
            }
        else:
            return {
                "status": "Routed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "message": "Unknown intent. Could not route request."
            }

    except Exception as e:
        return {"status": "Error", "error": str(e)}

