import time
from ddgs import DDGS

class WebSearchTool:
    """
    A tool to perform general web searches using duckduckgo-search.
    """
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, limit: int = 3) -> str:
        """
        Search the web and return a string snippet of top results.
        Includes basic error catching and rate-limit handling.
        """
        try:
            # We add a small sleep to avoid hitting rate limits instantly
            time.sleep(1)

            results = self.ddgs.text(query, max_results=limit)

            if not results:
                return "No web search results found."

            snippets = []
            for idx, res in enumerate(results):
                title = res.get("title", "No Title")
                href = res.get("href", "No Link")
                body = res.get("body", "No Body")
                snippets.append(f"Result {idx+1}:\nTitle: {title}\nURL: {href}\nSnippet: {body}")

            return "\n\n".join(snippets)

        except Exception as e:
            print(f"WebSearchTool Error: {e}")
            return f"Web search failed due to an error: {str(e)}"
