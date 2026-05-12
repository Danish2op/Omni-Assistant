import os
import json
from app.core.database import SupabaseClient
from dotenv import load_dotenv

load_dotenv()
db = SupabaseClient()
records = db.get_data("knowledge_base", {"limit": 10})
for r in records:
    print(r)
