import os
import requests


# Ordered by capability. Fallback on rate-limit/unavailable errors.
MODEL_FALLBACK_CHAIN = [
    "google/gemma-4-26b-a4b-it",
    "google/gemini-2.0-flash-001",
]

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class GeminiClient:
    """
    LLM client using OpenRouter API with model fallback chain.
    Name kept as GeminiClient to avoid breaking all agent imports.
    """

    def __init__(self):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables.")
        self.api_key = api_key

    def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Generate text response via OpenRouter with automatic model fallback.
        Tries each model in MODEL_FALLBACK_CHAIN until one succeeds.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://omni-agent.app",
            "X-Title": "Omni-Agent Neural Hub",
        }

        last_error = None
        for model_id in MODEL_FALLBACK_CHAIN:
            try:
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.7,
                }

                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )

                if response.status_code == 429 or response.status_code == 503:
                    print(f"Rate-limit/unavailable on {model_id}, trying next...")
                    last_error = f"HTTP {response.status_code}"
                    continue

                if response.status_code != 200:
                    error_msg = response.text[:200]
                    print(f"OpenRouter error ({model_id}): {response.status_code} - {error_msg}")
                    return f"Neural Core Error: API returned {response.status_code}."

                data = response.json()

                # Extract text from OpenAI-compatible response
                choices = data.get("choices", [])
                if not choices:
                    print(f"Warning: {model_id} returned empty choices for: {prompt[:50]}...")
                    return "The neural core returned an empty response."

                text = choices[0].get("message", {}).get("content", "")
                if not text:
                    return "The neural core blocked this response due to safety constraints."

                return text

            except requests.exceptions.Timeout:
                print(f"Timeout on {model_id}, trying next...")
                last_error = "Timeout"
                continue
            except Exception as e:
                last_error = e
                error_str = str(e)
                print(f"OpenRouter API Error ({model_id}): {error_str}")
                return f"Neural Core Error: {error_str}"

        # All models exhausted
        print(f"All models exhausted. Last error: {last_error}")
        return "Neural Core: All available models are currently at capacity. Please try again in a few minutes."
