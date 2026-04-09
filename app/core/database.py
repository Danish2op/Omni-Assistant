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
