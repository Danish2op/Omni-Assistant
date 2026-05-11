"""
V2 Archivist Agent — Metadata-Tagged Memory System.

Upgrades over V1:
- Stores memories with JSONB metadata (category, tags, agent_role, project)
- Filters retrieval by metadata tags for precision
- Uses V2 multi-model LLM client with GENERALIST role
- Graceful Supabase pause detection via SupabaseV2Client
"""

import json
from app.core.database_v2 import SupabaseV2Client
from app.core.llm_v2 import MultiModelClient, AgentRole


ARCHIVIST_SYSTEM_PROMPT = """You are the Archivist for Omni-Agent V2. You manage the user's knowledge base.

MISSION:
- If data contains the answer to the user's question, use it as the primary source.
- Do NOT explain your capabilities or architecture.
- Be surgical, direct, and factual.
- If no relevant records exist, say exactly: "I don't have any records about that in your memory."

FORMAT:
- Direct answer first.
- If multiple relevant records exist, use a concise bulleted list."""


class V2ArchivistAgent:
    def __init__(self):
        self.db = SupabaseV2Client()
        self.llm = MultiModelClient()
        self.table = "v2_memories"

    def handle_query(
        self,
        user_input: str,
        action: str = None,
        keywords: list = None,
        processed_query: str = None,
    ) -> str:
        keywords = keywords or []
        effective_query = processed_query if processed_query else user_input

        # Determine action
        if not action or action not in ("STORE", "RETRIEVE"):
            q_lower = effective_query.lower()
            if any(w in q_lower for w in ["remember", "save", "store", "note that", "keep in mind"]):
                action = "STORE"
            else:
                action = "RETRIEVE"

        if action == "STORE":
            return self._store(effective_query, user_input)
        elif action == "RETRIEVE":
            return self._retrieve(effective_query, keywords)

        return "I couldn't determine if you wanted to store or retrieve information."

    # ---- STORE with metadata ----
    def _store(self, effective_query: str, raw_input: str) -> str:
        extract_prompt = (
            f"Extract structured metadata from this message: '{effective_query}'.\n"
            "Return JSON with keys: 'category' (e.g., preference, note, fact, project, api_key), "
            "'content' (the actual info to store), "
            "'tags' (array of relevant keywords for future search).\n"
            "Respond with ONLY valid JSON."
        )
        extract_response = self.llm.generate(
            prompt=extract_prompt,
            system_instruction="Respond with ONLY valid JSON. No markdown.",
            role=AgentRole.GENERALIST,
            max_tokens=256,
            temperature=0.2,
        )

        try:
            cleaned = extract_response.replace("```json", "").replace("```", "").strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            data = json.loads(cleaned)
            category = data.get("category", "note")
            content = data.get("content", raw_input)
            tags = data.get("tags", [])
        except Exception:
            category = "note"
            content = raw_input
            tags = []

        # Build metadata-enriched record
        record = {
            "content": content,
            "metadata": json.dumps({
                "category": category,
                "tags": tags,
                "source": "user",
            }),
        }

        result = self.db.save_data(self.table, record)
        if result is None:
            return "⚠️ Memory storage is temporarily unavailable. The database may be paused — please check Supabase."
        if result:
            tag_str = ", ".join(tags[:3]) if tags else category
            return f"✅ Archived under **{category}** (tags: {tag_str}). I'll remember that."
        return "I tried to save that, but something went wrong. Please try again."

    # ---- RETRIEVE with metadata filtering ----
    def _retrieve(self, effective_query: str, keywords: list) -> str:
        # Extract keywords if not provided by router
        if not keywords:
            kw_prompt = (
                f"Extract search keywords from: '{effective_query}'. "
                "Return ONLY a JSON array of strings. No explanation."
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

        # Strategy: text search on content + metadata tag matching
        records = []
        if keywords:
            records = self.db.search_data(self.table, "content", keywords)
        else:
            records = self.db.get_data(self.table, {"limit": 20})

        # Pause detection
        if records is None:
            return "⚠️ Memory retrieval unavailable. The database may be paused — please check Supabase."

        # No-hallucination guard
        if not records:
            kw_str = ", ".join(keywords) if keywords else "that"
            return f"I don't have any records about {kw_str} in your memory."

        # Synthesize answer from matched records
        synthesis_prompt = (
            f"USER QUERY: {effective_query}\n"
            f"MATCHED RECORDS: {json.dumps(records, default=str)}\n"
        )
        response = self.llm.generate(
            prompt=synthesis_prompt,
            system_instruction=ARCHIVIST_SYSTEM_PROMPT,
            role=AgentRole.GENERALIST,
            max_tokens=1024,
        )
        return response if response else "I found records but couldn't synthesize an answer."
