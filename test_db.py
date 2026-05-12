import json
from app.core.database_v2 import SupabaseV2Client
db = SupabaseV2Client()
tasks = db.get_data("tasks", {"limit": 10})
print(json.dumps(tasks, indent=2))
