"""
V2 Organizer Agent — Task Management with Multi-Model + Graceful DB.

Uses GENERALIST role for extraction, SupabaseV2Client for pause detection.
Same CRUD logic as V1 but with resilient error handling.
"""

import json
from app.core.time_utils import format_ist_time
from app.core.database_v2 import SupabaseV2Client
from app.core.llm_v2 import MultiModelClient, AgentRole


ORGANIZER_SYSTEM_PROMPT = """You are the Organizer for Omni-Agent V2.

MISSION:
- If context contains predictions (sectors/stocks), use them to create relevant tasks.
- If purely a listing or update request, execute that.
- Output ONLY JSON for creation/update extraction."""


class V2OrganizerAgent:
    def __init__(self):
        self.db = SupabaseV2Client()
        self.llm = MultiModelClient()

    def handle_query(
        self,
        user_input: str,
        action: str = None,
        keywords: list = None,
        processed_query: str = None,
    ) -> str:
        current_time = format_ist_time()
        effective_query = processed_query if processed_query else user_input
        keywords = keywords or []

        # Determine action
        if not action or action not in ("CREATE", "LIST", "FILTER", "UPDATE"):
            q_lower = effective_query.lower()
            if any(w in q_lower for w in ["add", "create", "remind", "schedule"]):
                action = "CREATE"
            elif any(w in q_lower for w in ["update", "complete", "mark", "done", "finish"]):
                action = "UPDATE"
            elif any(w in q_lower for w in ["related to", "about", "filter", "search"]):
                action = "FILTER"
            else:
                action = "LIST"

        if action == "CREATE":
            return self._create_task(effective_query, user_input, current_time)
        elif action == "LIST":
            return self._list_tasks(user_input)
        elif action == "FILTER":
            return self._filter_tasks(keywords, user_input)
        elif action == "UPDATE":
            return self._update_task(user_input)

        return "I wasn't able to process that organizer request. Could you rephrase?"

    def _create_task(self, effective_query: str, raw_input: str, current_time: str) -> str:
        extract_prompt = (
            f"Current Time (IST): {current_time}\n"
            f"User Query: {raw_input}\n"
            f"Processing Context: {effective_query}\n\n"
            "MISSION: Extract task details into JSON.\n"
            "RULES:\n"
            "1. 'task_name': Clear title of the task.\n"
            "2. 'due_date': ISO 8601 format (e.g., '2024-05-13T09:00:00+05:30'). If no time is specified, default to 09:00:00 IST on the target date.\n"
            "3. 'priority': 'high', 'medium', or 'low'.\n\n"
            "Return ONLY JSON."
        )
        extract_response = self.llm.generate(
            prompt=extract_prompt,
            system_instruction="You are a precise data extractor. Output ONLY valid JSON.",
            role=AgentRole.GENERALIST,
            max_tokens=256,
            temperature=0.1,
        )

        try:
            if not extract_response:
                raise ValueError("Empty extraction")
            cleaned = extract_response.strip().replace("```json", "").replace("```", "")
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            data = json.loads(cleaned)
            insert_data = {
                "task_name": data.get("task_name", raw_input),
                "priority": data.get("priority", "medium"),
                "status": "pending",
                "due_date": data.get("due_date"),
            }
        except Exception as e:
            print(f"[V2 Organizer] Extract error: {e}")
            insert_data = {"task_name": raw_input, "status": "pending"}

        result = self.db.save_data("tasks", insert_data)
        if result is None:
            return "⚠️ Task management unavailable. Database may be paused — check Supabase."
        if result:
            return f"✅ Task added: {insert_data.get('task_name', raw_input)}"
        return "Failed to save task. Please try again."

    def _list_tasks(self, user_input: str) -> str:
        records = self.db.get_data("tasks", {"limit": 100})
        if records is None:
            return "⚠️ Task listing unavailable. Database may be paused — check Supabase."
        if not records:
            return "You have no pending tasks right now."

        synth_prompt = f"Records: {json.dumps(records, default=str)}\nRequest: {user_input}"
        response = self.llm.generate(
            prompt=synth_prompt,
            system_instruction="List tasks clearly. Use strikethrough for completed. Be concise.",
            role=AgentRole.GENERALIST,
            max_tokens=1024,
        )
        return response if response else "You have tasks, but I couldn't format them right now."

    def _filter_tasks(self, keywords: list, user_input: str) -> str:
        if not keywords:
            kw_prompt = (
                f"Extract search keywords from: '{user_input}'. "
                "Return ONLY a JSON array of strings."
            )
            kw_response = self.llm.generate(
                prompt=kw_prompt,
                role=AgentRole.GENERALIST,
                max_tokens=128,
                temperature=0.1,
            )
            try:
                cleaned = kw_response.strip().replace("```json", "").replace("```", "")
                keywords = json.loads(cleaned)
                if not isinstance(keywords, list):
                    keywords = []
            except Exception:
                keywords = []

        if not keywords:
            records = self.db.get_data("tasks", {"limit": 100})
        else:
            records = self.db.search_data("tasks", "task_name", keywords)

        if records is None:
            return "⚠️ Task filtering unavailable. Database may be paused."
        if not records:
            kw_str = ", ".join(keywords) if keywords else "that topic"
            return f"No tasks found related to {kw_str}."

        synth_prompt = (
            f"Filtered Records: {json.dumps(records, default=str)}\n"
            f"User Query: {user_input}\nFilter Keywords: {keywords}"
        )
        response = self.llm.generate(
            prompt=synth_prompt,
            system_instruction="Present ONLY filtered tasks matching keywords. Be concise.",
            role=AgentRole.GENERALIST,
            max_tokens=1024,
        )
        return response if response else f"Found {len(records)} matching tasks."

    def _update_task(self, user_input: str) -> str:
        records = self.db.get_data("tasks", {"status": "pending"})
        if records is None:
            return "⚠️ Task updates unavailable. Database may be paused."
        if not records:
            return "No pending tasks to update."

        find_prompt = (
            f"Tasks: {json.dumps(records, default=str)}\n"
            f"Request: {user_input}\n"
            'Return the task_id to complete as JSON: {"task_id": "..."}'
        )
        find_res = self.llm.generate(
            prompt=find_prompt,
            system_instruction="Output ONLY JSON.",
            role=AgentRole.GENERALIST,
            max_tokens=128,
            temperature=0.1,
        )
        try:
            if not find_res:
                raise ValueError("Empty find response")
            cleaned = find_res.strip().replace("```json", "").replace("```", "")
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            tid = json.loads(cleaned).get("task_id")
            if tid:
                self.db.update_data("tasks", {"id": tid}, {"status": "completed"})
                return "✅ Task marked as completed."
        except Exception as e:
            print(f"[V2 Organizer] Update error: {e}")
        return "I couldn't identify a pending task to update."
