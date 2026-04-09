import json
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient

ARCHIVIST_SYSTEM_PROMPT = """You are the Archivist for the Omni-Agent Neural Hub. You have retrieved the following data from the user's memory.

MISSION:
- If the data contains the direct answer to the user's question, you MUST use it as the primary source.
- Do NOT explain your capabilities, architecture, or agent design.
- Be surgical, direct, and factual.
- If the provided data does NOT contain relevant information, say exactly: "I don't have any records about that in your memory."

FORMAT:
- Direct answer first.
- If multiple relevant records exist, use a concise bulleted list."""


class ArchivistAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, action: str = None, keywords: list = None, processed_query: str = None) -> str:
        keywords = keywords or []
        effective_query = processed_query if processed_query else user_input

        # Use Router's action directly
        if not action or action not in ("STORE", "RETRIEVE"):
            q_lower = effective_query.lower()
            if any(w in q_lower for w in ["remember", "save", "store", "note that", "keep in mind"]):
                action = "STORE"
            else:
                action = "RETRIEVE"

        # ---- STORE ----
        if action == "STORE":
            extract_prompt = (
                f"Extract a category (e.g., 'preference', 'note', 'fact') and the content from this message: "
                f"'{effective_query}'. Format as JSON with exactly two keys: 'category' and 'content'."
            )
            extract_response = self.llm.generate_response(
                prompt=extract_prompt, 
                system_instruction="Respond with ONLY valid JSON. No markdown formatting."
            )
            
            try:
                clean_raw = extract_response.replace('```json', '').replace('```', '').strip()
                start = clean_raw.find('{')
                end = clean_raw.rfind('}')
                if start != -1 and end != -1:
                    clean_raw = clean_raw[start:end+1]
                data = json.loads(clean_raw)
                category = data.get("category", "note")
                content = data.get("content", user_input)
            except Exception:
                category = "note"
                content = user_input
                
            self.db_client.save_data('knowledge_base', {
                "category": category,
                "content": content
            })
            return "Knowledge archived. I've noted that down for you."
            
        # ---- RETRIEVE ----
        elif action == "RETRIEVE":
            # Keyword-scoped retrieval instead of dumping all records
            if not keywords:
                # Extract keywords from query as fallback
                kw_prompt = (
                    f"Extract search keywords from: '{effective_query}'. "
                    "Return ONLY a JSON array of strings. No explanation."
                )
                kw_response = self.llm.generate_response(prompt=kw_prompt)
                try:
                    cleaned = kw_response.strip().replace('```json', '').replace('```', '')
                    keywords = json.loads(cleaned)
                    if not isinstance(keywords, list):
                        keywords = []
                except Exception:
                    keywords = []

            # Search with keywords if available, otherwise get recent records
            if keywords:
                records = self.db_client.search_data('knowledge_base', 'content', keywords)
            else:
                records = self.db_client.get_data('knowledge_base', {"limit": 50})

            # NO-HALLUCINATION GUARD: If zero records match, return clean message
            if not records:
                kw_str = ", ".join(keywords) if keywords else "that"
                return f"I don't have any records about {kw_str} in your memory."

            # Synthesize answer from matched records only
            synthesis_prompt = (
                f"USER QUERY: {effective_query}\n"
                f"MATCHED RECORDS: {json.dumps(records, default=str)}\n"
            )
            response = self.llm.generate_response(
                prompt=synthesis_prompt, 
                system_instruction=ARCHIVIST_SYSTEM_PROMPT
            )
            return response if response else "I found records but couldn't synthesize an answer."
        
        return "I couldn't determine if you wanted to store or retrieve information."

