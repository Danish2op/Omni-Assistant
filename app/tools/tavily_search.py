import os
from tavily import TavilyClient

class TavilySearchTool:
    """
    A tool to perform general web searches using the Tavily API.
    """
    def __init__(self):
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            print("Warning: TAVILY_API_KEY environment variable not found.")
        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str, limit: int = 3) -> str:
        """
        Search the web and return a string snippet of top results.
        Includes basic error catching and rate-limit handling.
        """
        try:
            # We use advanced search for better quality, limit the number of results
            response = self.client.search(query, search_depth="advanced", max_results=limit)
            
            results = response.get("results", [])
            if not results:
                return "No web search results found."

            snippets = []
            for idx, res in enumerate(results):
                title = res.get("title", "No Title")
                href = res.get("url", "No Link")
                body = res.get("content", "No Content")
                snippets.append(f"Result {idx+1}:\nTitle: {title}\nURL: {href}\nSnippet: {body}")
            
            return "\n\n".join(snippets)

        except Exception as e:
            print(f"TavilySearchTool Error: {e}")
            return f"Web search failed due to an error: {str(e)}"
