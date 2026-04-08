from fastapi import FastAPI
from dotenv import load_dotenv
import os
from app.core.database import SupabaseClient

# Load environment variables
load_dotenv()

app = FastAPI()
db_client = SupabaseClient()

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
