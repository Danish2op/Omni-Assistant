import json
from app.core.time_utils import format_ist_time
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

    def handle_query(self, user_input: str, action: str = None, keywords: list = None, processed_query: str = None) -> str:
        current_time = format_ist_time()
        effective_query = processed_query if processed_query else user_input
        keywords = keywords or []

        # Use Router's action directly — no secondary LLM call needed
        if not action or action not in ("CREATE", "LIST", "FILTER", "UPDATE"):
            # Fallback: infer from keywords in the query itself
            q_lower = effective_query.lower()
            if any(w in q_lower for w in ["add", "create", "remind", "schedule"]):
                action = "CREATE"
            elif any(w in q_lower for w in ["update", "complete", "mark", "done", "finish"]):
                action = "UPDATE"
            elif any(w in q_lower for w in ["related to", "about", "filter", "search"]):
                action = "FILTER"
            else:
                action = "LIST"

        # ---- CREATE ----
        if action == "CREATE":
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
                start = cleaned.find('{')
                end = cleaned.rfind('}')
                if start != -1 and end != -1:
                    cleaned = cleaned[start:end+1]
                data = json.loads(cleaned)
                insert_data = {
                    "task_name": data.get("task_name", user_input),
                    "priority": data.get("priority", "medium"),
                    "status": "pending",
                    "due_date": data.get("due_date")
                }
                result = self.db_client.save_data('tasks', insert_data)
                if result:
                    return f"Successfully added task: {insert_data['task_name']}"
                else:
                    return "I prepared the task but the database connection failed. Please try again later."
            except Exception as e:
                print(f"Organizer Extract Error: {e}")
                result = self.db_client.save_data('tasks', {"task_name": user_input, "status": "pending"})
                if result:
                    return "Task added to dashboard."
                else:
                    return "I couldn't save the task due to a database issue. Please try again later."

        # ---- FILTER ----
        elif action == "FILTER":
            return self._filter_tasks(keywords, user_input)
                
        # ---- LIST ----
        elif action == "LIST":
            records = self.db_client.get_data('tasks', {"limit": 100})
            if not records:
                return "You have no pending tasks right now."
            synth_prompt = f"Records: {json.dumps(records, default=str)}\nRequest: {user_input}"
            response = self.llm.generate_response(
                prompt=synth_prompt, 
                system_instruction="List tasks clearly. Use strikethrough for completed. Be concise."
            )
            return response if response else "You have tasks, but I couldn't format them right now."

        # ---- UPDATE ----
        elif action == "UPDATE":
            records = self.db_client.get_data('tasks', {"status": "pending"})
            if not records:
                return "No pending tasks to update."
            find_prompt = (
                f"Tasks: {json.dumps(records, default=str)}\n"
                f"Request: {user_input}\n"
                "Return the task_id to complete as JSON: {\"task_id\": \"...\"}"
            )
            find_res = self.llm.generate_response(prompt=find_prompt, system_instruction="Output ONLY JSON.")
            try:
                if not find_res:
                    raise ValueError("Empty find response")
                cleaned = find_res.strip().replace('```json', '').replace('```', '')
                start = cleaned.find('{')
                end = cleaned.rfind('}')
                if start != -1 and end != -1:
                    cleaned = cleaned[start:end+1]
                tid = json.loads(cleaned).get('task_id')
                if tid:
                    self.db_client.update_data("tasks", {"id": tid}, {"status": "completed"})
                    return "Task marked as completed."
            except Exception as e:
                print(f"Organizer Update Error: {e}")
            return "I couldn't identify a pending task to update."

        return "I wasn't able to process that organizer request. Could you rephrase?"

    def _filter_tasks(self, keywords: list, user_input: str) -> str:
        """Filter tasks by keywords using database-level search."""
        if not keywords:
            # Extract keywords from the query as a fallback
            extract_prompt = (
                f"Extract search keywords from this query: '{user_input}'. "
                "Return ONLY a JSON array of strings, e.g. [\"stocks\", \"market\"]. No explanation."
            )
            kw_response = self.llm.generate_response(prompt=extract_prompt)
            try:
                cleaned = kw_response.strip().replace('```json', '').replace('```', '')
                keywords = json.loads(cleaned)
                if not isinstance(keywords, list):
                    keywords = []
            except Exception:
                keywords = []

        if not keywords:
            # Can't filter without keywords, fall back to full list
            records = self.db_client.get_data('tasks', {"limit": 100})
        else:
            records = self.db_client.search_data('tasks', 'task_name', keywords)

        if not records:
            kw_str = ", ".join(keywords) if keywords else "that topic"
            return f"I checked your tasks, but none of them are related to {kw_str}."

        synth_prompt = (
            f"Filtered Records: {json.dumps(records, default=str)}\n"
            f"User Query: {user_input}\n"
            f"Filter Keywords: {keywords}"
        )
        response = self.llm.generate_response(
            prompt=synth_prompt,
            system_instruction="Present ONLY the filtered tasks that match the keywords. Be concise and direct."
        )
        return response if response else f"Found {len(records)} tasks matching your filter, but couldn't format them."

