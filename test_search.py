import os
import json
from app.core.database_v2 import SupabaseV2Client
from dotenv import load_dotenv

load_dotenv()

db = SupabaseV2Client()
print("Keywords: ['interview', 'preparing']")
records = db.search_data("v2_memories", "content", ["interview", "preparing"])
print(f"Result count: {len(records)}")
for r in records:
    print(r)
