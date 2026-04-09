import os
from supabase import create_client, Client

class SupabaseClient:
    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables.")
        self.client: Client = create_client(supabase_url, supabase_key)

    def save_data(self, table_name: str, data: dict):
        try:
            response = self.client.table(table_name).insert(data).execute()
            return response.data
        except Exception as e:
            print(f"Supabase Save Error: {e}")
            return None

    def get_data(self, table_name: str, query_filter: dict):
        try:
            query = self.client.table(table_name).select("*")
            for key, value in query_filter.items():
                if key == "limit":
                    query = query.limit(value)
                else:
                    query = query.eq(key, value)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Supabase Get Error: {e}")
            return []

    def update_data(self, table_name: str, query_filter: dict, data: dict):
        try:
            query = self.client.table(table_name).update(data)
            for key, value in query_filter.items():
                query = query.eq(key, value)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Supabase Update Error: {e}")
            return None

    def search_data(self, table_name: str, column: str, keywords: list, limit: int = 50):
        """
        Search a table column for rows matching ANY of the given keywords using ilike.
        Returns matching rows, or an empty list if nothing matches.
        """
        try:
            if not keywords:
                return self.get_data(table_name, {"limit": limit})

            # Build OR filter: column.ilike.%keyword1%,column.ilike.%keyword2%
            or_clauses = ",".join([f"{column}.ilike.%{kw}%" for kw in keywords])
            response = (
                self.client.table(table_name)
                .select("*")
                .or_(or_clauses)
                .limit(limit)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"Supabase Search Error: {e}")
            return []

    def delete_data(self, table_name: str, query_filter: dict):
        try:
            query = self.client.table(table_name).delete()
            for key, value in query_filter.items():
                query = query.eq(key, value)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Supabase Delete Error: {e}")
            return None
