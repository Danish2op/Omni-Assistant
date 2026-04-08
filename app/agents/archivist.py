import json
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient

class ArchivistAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, pre_intent: str = None, processed_query: str = None) -> str:
        # Action A: Determine Intent
        if pre_intent and pre_intent != "UNKNOWN":
            intent = pre_intent
        else:
            intent_prompt = (
                f"Analyze this user input: '{user_input}'. "
                "Does the user want to save/remember something (STORE) or find/recall something (RETRIEVE)? "
                "Respond with only 'STORE' or 'RETRIEVE'."
            )
            intent_response = self.llm.generate_response(prompt=intent_prompt)
            intent = intent_response.strip().upper()

        effective_query = processed_query if processed_query else user_input

        # Action B: Execution
        if "STORE" in intent:
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
            return "I've noted that down in your knowledge base."
            
        elif "RETRIEVE" in intent:
            keyword_prompt = (
                f"Extract a search_keyword from this message: '{effective_query}'. "
                "Format as JSON with key 'search_keyword'."
            )
            keyword_response = self.llm.generate_response(
                prompt=keyword_prompt, 
                system_instruction="Respond with ONLY valid JSON. No markdown formatting."
            )
            
            try:
                clean_raw = keyword_response.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_raw)
                search_keyword = data.get("search_keyword", "")
            except Exception:
                search_keyword = ""

            # Fetch the latest items safely. since eq() is rigid, we grab records and let LLM synthesize.
            query_filter = {"limit": 100} 
            records = self.db_client.get_data('knowledge_base', query_filter)
            
            synth_prompt = (
                f"You are the Archivist of the Omni-Agent knowledge base.\n"
                f"Your mission: Provide a natural, insightful answer based ONLY on the User Query and the Knowledge Records provided below.\n\n"
                f"USER QUERY: {effective_query}\n"
                f"KNOWLEDGE RECORDS:\n{json.dumps(records, default=str)}\n\n"
                "RULES:\n"
                "1. If the user asks 'What do you have in my knowledge base?', 'What do you remember?', or similar, you MUST list and summarize ALL relevant records.\n"
                "2. DO NOT describe your 'three functional pillars', internal mechanisms, or agent architecture.\n"
                "3. If information is missing, state it clearly but check if any partial matches exist.\n"
                "4. Be professional, concise, and direct."
            )
            return self.llm.generate_response(
                prompt=synth_prompt, 
                system_instruction="You are the Archivist agent. Summarize user data with high accuracy. Do not talk about yourself."
            )
        
        return "I could not determine if you wanted to STORE or RETRIEVE information."
