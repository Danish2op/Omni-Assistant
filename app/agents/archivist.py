import json
from app.core.database import SupabaseClient
from app.core.llm import GeminiClient

ARCHIVIST_SYSTEM_PROMPT = """You are the Archivist for the Omni-Agent Neural Hub. You have retrieved the following data from the user's memory: [DATA]. 

MISSION:
- If the data contains the direct answer to the user's question, you MUST use it as the primary source.
- Do NOT explain your capabilities, three functional pillars, or agent architecture.
- Be surgical, direct, and factual.
- If NO data is found in the provided records that matches the query, say: 'I couldn't find that in your records.'—do NOT hallucinate or provide a general/generic answer.

FORMAT:
- Direct answer first.
- If multiple relevant records exist, use a concise bulleted list."""


class ArchivistAgent:
    def __init__(self):
        self.db_client = SupabaseClient()
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, pre_intent: str = None, processed_query: str = None) -> str:
        # Step 1: Specific Action Classification (STORE vs RETRIEVE)
        if pre_intent and pre_intent in ["STORE", "RETRIEVE"]:
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
            return "Knowledge archived. I've noted that down for you."
            
        elif "RETRIEVE" in intent:
            # Forced Retrieval Loop
            query_filter = {"limit": 100} 
            records = self.db_client.get_data('knowledge_base', query_filter)
            
            # Synthesis Phase with Strict Data-First Constraint
            synthesis_prompt = (
                f"USER QUERY: {effective_query}\n"
                f"RETRIVED KNOWLEDGE RECORDS: {json.dumps(records, default=str)}\n"
            )
            
            return self.llm.generate_response(
                prompt=synthesis_prompt, 
                system_instruction=ARCHIVIST_SYSTEM_PROMPT
            )
        
        return "I couldn't identify if you wanted to store or retrieve that information from your memory bank."
