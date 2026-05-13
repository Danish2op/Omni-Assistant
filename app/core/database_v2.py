"""
V2 Database Client with Graceful Degradation for Supabase Free Tier.

Detects Supabase inactivity pauses and returns friendly admin alerts
instead of crashing the API.
"""

import os
from supabase import create_client, Client
from typing import Optional


SUPABASE_PAUSED_MSG = (
    "⚠️ Memory database is currently paused due to inactivity. "
    "Please ask the Admin to unpause it in the Supabase dashboard."
)


class SupabaseV2Client:
    """
    Supabase client with enhanced metadata filtering and graceful degradation.

    Wraps all DB calls in connection-aware try/except blocks.
    If Supabase is paused (free tier 7-day inactivity), returns
    a friendly admin alert instead of crashing.
    """

    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found.")
        self.client: Client = create_client(supabase_url, supabase_key)
        self._is_paused = False

    def _handle_connection_error(self, error: Exception, operation: str) -> None:
        """Detect Supabase pause vs other errors."""
        error_str = str(error).lower()
        connection_indicators = [
            "timeout", "connection refused", "name resolution",
            "connect call failed", "gaierror", "connectionerror",
            "project is paused", "502", "503", "504"
        ]
        if any(indicator in error_str for indicator in connection_indicators):
            self._is_paused = True
            print(f"[V2 DB] Supabase appears PAUSED. Operation: {operation}. Error: {error}")
        else:
            print(f"[V2 DB] Error in {operation}: {error}")
            print(f"[V2 DB] Full Exception Details: {repr(error)}")

    @property
    def is_paused(self) -> bool:
        """Check if Supabase has been detected as paused."""
        return self._is_paused

    def save_data(self, table_name: str, data: dict) -> Optional[list]:
        """Insert data with pause detection."""
        try:
            response = self.client.table(table_name).insert(data).execute()
            self._is_paused = False  # Connection works -> reset flag
            return response.data
        except Exception as e:
            self._handle_connection_error(e, f"save_data({table_name})")
            return None

    def get_data(self, table_name: str, query_filter: dict) -> list:
        """Fetch data with pause detection."""
        try:
            query = self.client.table(table_name).select("*")
            for key, value in query_filter.items():
                if key == "limit":
                    query = query.limit(value)
                else:
                    query = query.eq(key, value)
            response = query.execute()
            self._is_paused = False
            return response.data
        except Exception as e:
            self._handle_connection_error(e, f"get_data({table_name})")
            return []

    def update_data(self, table_name: str, query_filter: dict, data: dict) -> Optional[list]:
        """Update data with pause detection."""
        try:
            query = self.client.table(table_name).update(data)
            for key, value in query_filter.items():
                query = query.eq(key, value)
            response = query.execute()
            self._is_paused = False
            return response.data
        except Exception as e:
            self._handle_connection_error(e, f"update_data({table_name})")
            return None

    def search_data(self, table_name: str, column: str, keywords: list, limit: int = 50) -> list:
        """Search with keyword matching and pause detection."""
        try:
            if not keywords:
                return self.get_data(table_name, {"limit": limit})
            
            # tables that support metadata searching
            supports_metadata = table_name.lower() in ["memories", "tasks", "knowledge_base", "v2_memories"]
            
            if supports_metadata:
                or_clauses = ",".join([
                    f"{column}.ilike.%{kw}%,"
                    f"metadata->>tags.ilike.%{kw}%,"
                    f"metadata->>category.ilike.%{kw}%"
                    for kw in keywords
                ])
            else:
                or_clauses = ",".join([f"{column}.ilike.%{kw}%" for kw in keywords])
            
            response = (
                self.client.table(table_name)
                .select("*")
                .or_(or_clauses)
                .limit(limit)
                .execute()
            )
            self._is_paused = False
            return response.data if response.data else []
        except Exception as e:
            self._handle_connection_error(e, f"search_data({table_name})")
            return []

    def delete_data(self, table_name: str, query_filter: dict) -> Optional[list]:
        """Delete data with pause detection."""
        try:
            query = self.client.table(table_name).delete()
            for key, value in query_filter.items():
                query = query.eq(key, value)
            response = query.execute()
            self._is_paused = False
            return response.data
        except Exception as e:
            self._handle_connection_error(e, f"delete_data({table_name})")
            return None

    def get_pause_message(self) -> str:
        """Return friendly admin alert if paused."""
        return SUPABASE_PAUSED_MSG if self._is_paused else ""
