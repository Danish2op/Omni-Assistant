import json
from datetime import datetime
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient

class OrganizerAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, pre_intent: str = None, processed_query: str = None) -> str:
        # Action A: Intent Analysis
        # Ensure we only use pre_intent if it is a specific action. 
        # If it is just the high-level "ORGANIZER", we must classify it into CREATE/LIST/UPDATE.
        if pre_intent and pre_intent in ["CREATE", "LIST", "UPDATE"]:
            intent = pre_intent
        else:
            intent_prompt = (
                f"Analyze this user input: '{user_input}'. "
                "Does the user want to CREATE a task, LIST/view tasks, or UPDATE/mark a task as done? "
                "Respond with only 'CREATE', 'LIST', or 'UPDATE'."
            )
            intent_response = self.llm.generate_response(prompt=intent_prompt)
            intent = intent_response.strip().upper()

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        effective_query = processed_query if processed_query else user_input

        # Action B: Execution
        if "CREATE" in intent:
            extract_prompt = (
                f"Extract task details from this message: '{effective_query}'. "
                f"The current reference time is {current_time}. "
                "Format as JSON with exactly three keys: 'task_name' (string), 'due_date' (ISO timestamp string including time if mentioned, or null if unmentioned), and 'priority' (string: 'high', 'medium', or 'low'). "
                "If only a date is mentioned without time, default to 09:00:00 for that date."
            )
            extract_response = self.llm.generate_response(
                prompt=extract_prompt, 
                system_instruction="Respond with ONLY valid JSON. No markdown formatting."
            )
            try:
                clean_raw = extract_response.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_raw)
                
                task_name = data.get("task_name")
                if not task_name:
                    task_name = user_input
                due_date = data.get("due_date") 
                priority = data.get("priority", "medium")

                insert_data = {
                    "task_name": task_name,
                    "priority": priority,
                    "status": "pending"
                }
                if due_date:
                    insert_data["due_date"] = due_date
                    
                self.db_client.save_data('tasks', insert_data)
                return "I've added that to your tasks schedule."
            except Exception:
                return "Failed to parse task details, but I see you want to create a task."
                
        elif "LIST" in intent:
            query_filter = {"limit": 100} 
            records = self.db_client.get_data('tasks', query_filter)
            
            synth_prompt = (
                f"You are the Organizer for the Omni-Agent. Format the user's task list.\n"
                f"User Request: {effective_query}\n"
                f"Task Records:\n{json.dumps(records, default=str)}\n\n"
                "INSTRUCTIONS:\n"
                "1. Return a clean, simple bulleted list of tasks.\n"
                "2. FORMAT: - **[Task Name]** | Due: [Date and Time] | Status: [Status] | Priority: [Priority]\n"
                "3. If using a table, ensure property markdown row spacing (new lines between rows).\n"
                "4. Use strikethrough ~~task~~ for completed items.\n"
                "5. Ensure the output is professional and easy to scan."
            )
            return self.llm.generate_response(
                prompt=synth_prompt, 
                system_instruction="You are the Organizer agent. Output EXACTLY the requested format. No fluff."
            )

        elif "UPDATE" in intent:
            # Find task ID to update
            records = self.db_client.get_data('tasks', {"status": "pending"})
            
            find_prompt = (
                f"The user wants to update a task status to completed based on this message: '{effective_query}'.\n"
                f"Here are the current pending tasks:\n{json.dumps(records, default=str)}\n\n"
                f"Identify the ID of the task they completed. Format as JSON with key 'task_id'. Return null if none match."
            )
            find_response = self.llm.generate_response(
                prompt=find_prompt, 
                system_instruction="Respond with ONLY valid JSON. No markdown formatting."
            )
            try:
                clean_raw = find_response.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_raw)
                target_id = data.get("task_id")
                
                if target_id:
                    self.db_client.update_data("tasks", {"id": target_id}, {"status": "completed"})
                    return "I've marked that task as completed."
                else:
                    return "I couldn't find a matching pending task to update."
            except Exception:
                return "Failed to identify a specific task to update."
        
        return "I could not determine if you wanted to CREATE, LIST, or UPDATE your tasks."
