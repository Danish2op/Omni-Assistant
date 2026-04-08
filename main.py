from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel
import os
from app.core.database import SupabaseClient
from app.agents.router import RouterAgent
from app.agents.analyst import AnalystAgent
from app.agents.archivist import ArchivistAgent

# Load environment variables
load_dotenv()

app = FastAPI()
db_client = SupabaseClient()
router_agent = RouterAgent()
analyst_agent = AnalystAgent()
archivist_agent = ArchivistAgent()


class ChatRequest(BaseModel):
    message: str


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

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        # Step 1: Route the request
        result = router_agent.route_request(request.message)
        intent = result.get("intent", "UNKNOWN")

        # Step 2: Dispatch to the appropriate sub-agent
        if intent == "ANALYST":
            answer = analyst_agent.handle_query(request.message)
            return {
                "status": "Completed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "response": answer
            }
        elif intent == "ARCHIVIST":
            answer = archivist_agent.handle_query(request.message)
            return {
                "status": "Completed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "response": answer
            }
        elif intent == "ORGANIZER":
            return {
                "status": "Routed",
                "intent": intent,
                "reasoning": result.get("reasoning", ""),
                "message": "Organizer agent not yet implemented."
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

