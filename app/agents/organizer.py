import json
from datetime import datetime
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient


ORGANIZER_SYSTEM_PROMPT = """You are the Organizer for Omni-Assistant. 

MISSION:
- If context contains predictions (sectors/stocks), use them to create relevant tasks.
- If purely a listing or update request, execute that.
- Output ONLY JSON for creation/update extraction."""


class OrganizerAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, pre_intent: str = None, processed_query: str = None) -> str:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        effective_query = processed_query if processed_query else user_input

        # Action: Consolidated Intent & Extraction
        # If pre_intent is provided, we skip "asking" the LLM what to do
        intent = pre_intent if pre_intent in ["CREATE", "LIST", "UPDATE"] else None
        
        if not intent:
            # Fallback if Router didn't specify sub-intent
            intent_prompt = f"Analyze: '{effective_query}'. Is this CREATE, LIST, or UPDATE? Return ONLY the word."
            res = self.llm.generate_response(prompt=intent_prompt)
            intent = res.strip().upper() if res else "CREATE"

        if "CREATE" in intent:
            # Single-call extraction
            extract_prompt = (
                f"Reference Time: {current_time}\n"
                f"Query/Context: {effective_query}\n\n"
                "Extract into JSON: {'task_name', 'due_date', 'priority'}. "
                "Include any predicted stock/sector info from context in task_name."
            )
            extract_response = self.llm.generate_response(
                prompt=extract_prompt, 
                system_instruction="Provide ONLY valid JSON."
            )
            
            try:
                if not extract_response:
                    raise ValueError("Empty extraction response")
                cleaned = extract_response.strip().replace('```json', '').replace('```', '')
                data = json.loads(cleaned)
                insert_data = {
                    "task_name": data.get("task_name", user_input),
                    "priority": data.get("priority", "medium"),
                    "status": "pending",
                    "due_date": data.get("due_date")
                }
                self.db_client.save_data('tasks', insert_data)
                return f"Successfully added task: {insert_data['task_name']}"
            except Exception as e:
                print(f"Organizer Extract Error: {e}")
                self.db_client.save_data('tasks', {"task_name": user_input, "status": "pending"})
                return "Task added to dashboard."
                
        elif "LIST" in intent:
            records = self.db_client.get_data('tasks', {"limit": 100})
            if not records:
                return "You have no pending tasks today."
            synth_prompt = f"Records: {json.dumps(records, default=str)}\nRequest: {user_input}"
            return self.llm.generate_response(
                prompt=synth_prompt, 
                system_instruction="List tasks beautifully. Use strikethrough for completed."
            )

        elif "UPDATE" in intent:
            records = self.db_client.get_data('tasks', {"status": "pending"})
            if not records:
                return "No pending tasks to update."
            find_prompt = f"Tasks: {json.dumps(records, default=str)}\nRequest: {user_input}\nReturn task_id to complete. JSON: {'task_id': '...'}"
            find_res = self.llm.generate_response(prompt=find_prompt, system_instruction="Output ONLY JSON.")
            try:
                if not find_res:
                    raise ValueError("Empty find response")
                tid = json.loads(find_res.strip().replace('```json', '').replace('```', '')).get('task_id')
                if tid:
                    self.db_client.update_data("tasks", {"id": tid}, {"status": "completed"})
                    return "Task marked as completed."
            except:
                pass
            return "I couldn't identify a pending task to update."

        return "I'm not sure how to organize that. Can you please rephrase your request? or breake it in 2-3 queries"
