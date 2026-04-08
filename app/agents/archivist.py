import json
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient

class ArchivistAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str) -> str:
        # Action A: Determine Intent
        intent_prompt = (
            f"Analyze this user input: '{user_input}'. "
            "Does the user want to save/remember something (STORE) or find/recall something (RETRIEVE)? "
            "Respond with only 'STORE' or 'RETRIEVE'."
        )
        intent_response = self.llm.generate_response(prompt=intent_prompt)
        intent = intent_response.strip().upper()

        # Action B: Execution
        if "STORE" in intent:
            extract_prompt = (
                f"Extract a category (e.g., 'preference', 'note', 'fact') and the content from this message: "
                f"'{user_input}'. Format as JSON with exactly two keys: 'category' and 'content'."
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
                f"Extract a search_keyword from this message: '{user_input}'. "
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
                f"You need to answer the user's query based on the knowledge base records.\n"
                f"User Query: {user_input}\n"
                f"Search Keyword Extracted: {search_keyword}\n\n"
                f"Records:\n{json.dumps(records, default=str)}\n\n"
                "Synthesize a natural answer. If the information is not present in the records, politely inform the user that you couldn't find that information."
            )
            return self.llm.generate_response(
                prompt=synth_prompt, 
                system_instruction="You are the Archivist agent. Provide concise, helpful answers."
            )
        
        return "I could not determine if you wanted to STORE or RETRIEVE information."
