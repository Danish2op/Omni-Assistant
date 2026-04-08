import json
from datetime import datetime
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient


ORGANIZER_SYSTEM_PROMPT = """You are the Organizer for Omni-Assistant. 

MISSION:
- If [NEURAL_CONTEXT_FROM_PREVIOUS_STEP] is provided, you MUST extract any predicted sectors, stock tickers, or actionable advice and use it to populate the task details.
- Be precise with dates and priorities.
- Do NOT explain your logic. Just execute the action."""


class OrganizerAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, pre_intent: str = None, processed_query: str = None) -> str:
        # Action A: Intent Analysis
        # Determine internal sub-intent
        if pre_intent and pre_intent in ["CREATE", "LIST", "UPDATE"]:
            intent = pre_intent
        else:
            intent_prompt = (
                f"Analyze this query: '{processed_query if processed_query else user_input}'. "
                "Does it involve CREATING a new task, LISTING existing tasks, or UPDATING a task? "
                "Respond with ONLY 'CREATE', 'LIST', or 'UPDATE'."
            )
            intent_response = self.llm.generate_response(prompt=intent_prompt)
            intent = intent_response.strip().upper()

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        effective_query = processed_query if processed_query else user_input

        # Action B: Execution
        if "CREATE" in intent:
            extract_prompt = (
                f"Reference Time: {current_time}\n"
                f"Query & Context: {effective_query}\n\n"
                "INSTRUCTION: Extract task details into JSON with keys: 'task_name', 'due_date' (ISO), 'priority'. "
                "If the context mentions a specific sector or stock to invest in, put that in the 'task_name'."
            )
            extract_response = self.llm.generate_response(
                prompt=extract_prompt, 
                system_instruction="Provide ONLY valid JSON. No markdown."
            )
            
            try:
                # Cleaning for robustness
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
            except Exception:
                # Fallback on parse failure
                self.db_client.save_data('tasks', {"task_name": user_input, "status": "pending"})
                return "Task added to your board."
                
        elif "LIST" in intent:
            records = self.db_client.get_data('tasks', {"limit": 100})
            synth_prompt = f"User Request: {user_input}\nRecords: {json.dumps(records, default=str)}"
            return self.llm.generate_response(
                prompt=synth_prompt, 
                system_instruction="List the tasks beautifully and concisely. Use strikethrough for completed ones."
            )

        elif "UPDATE" in intent:
            # Find and mark pending task as completed
            records = self.db_client.get_data('tasks', {"status": "pending"})
            find_prompt = f"Tasks: {json.dumps(records, default=str)}\nRequest: {user_input}\nReturn only the task_id to complete in JSON: {{'task_id': '...'}}"
            find_res = self.llm.generate_response(prompt=find_prompt, system_instruction="Output ONLY JSON.")
            try:
                tid = json.loads(find_res.strip().replace('```json', '').replace('```', '')).get('task_id')
                if tid:
                    self.db_client.update_data("tasks", {"id": tid}, {"status": "completed"})
                    return "Task marked as completed."
            except:
                pass
            return "I couldn't identify a specific pending task to update."

        return "I'm not sure if you want to create, list, or update tasks."
