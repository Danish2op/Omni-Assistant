import os
from google import genai
from google.genai import types


# Ordered by capability. If one is quota-exhausted, try the next.
MODEL_FALLBACK_CHAIN = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-lite",
]


class GeminiClient:
    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        self.client = genai.Client(api_key=api_key)

    def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Generate a text response with automatic model fallback on quota exhaustion.
        Tries each model in MODEL_FALLBACK_CHAIN until one succeeds.
        """
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        last_error = None
        for model_id in MODEL_FALLBACK_CHAIN:
            try:
                response = self.client.models.generate_content(
                    model=model_id, 
                    contents=prompt,
                    config=config
                )

                if not response or not response.text:
                    print(f"Warning: {model_id} returned empty/blocked response for: {prompt[:50]}...")
                    return "The neural core blocked this response due to safety constraints."

                return response.text

            except Exception as e:
                last_error = e
                error_str = str(e)
                # Only fallback on quota/availability errors, not on other failures
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str or "UNAVAILABLE" in error_str:
                    print(f"Quota/Availability limit on {model_id}, trying next model...")
                    continue
                else:
                    # Non-quota error — don't retry, return immediately
                    print(f"Gemini API Error ({model_id}): {error_str}")
                    return f"Neural Core Error: System was unable to synthesize a response. ({error_str})"

        # All models exhausted
        print(f"All models exhausted. Last error: {last_error}")
        return "Neural Core: All available models are currently at capacity. Please try again in a few minutes."

