import os
import json
from app.core.database_v2 import SupabaseV2Client
from dotenv import load_dotenv

load_dotenv()
db = SupabaseV2Client()

try:
    response = db.client.table("v2_memories").select("*").execute()
    for r in response.data:
        print(r['id'], type(r.get('metadata')))
except Exception as e:
    print(e)
