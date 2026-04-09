import os
from google import genai
from google.genai import types


class GeminiClient:
    def __init__(self):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        self.client = genai.Client(api_key=api_key)

    def generate_response(self, prompt: str, system_instruction: str = None) -> str:
        """
        Generate a text response with inherent None-safety and Model 1.5 Flash precision.
        """
        try:
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction
                )

            # UPGRADE: Using Gemini 1.5 Flash for better reasoning/JSON adherence
            response = self.client.models.generate_content(
                model="models/gemini-flash-latest", 
                contents=prompt,
                config=config
            )

            # RESILIENCE: response.text can be None if safety filters block it
            if not response or not response.text:
                print(f"Warning: Gemini returned empty/blocked response for prompt: {prompt[:50]}...")
                return "The neural core blocked this response due to high sensitivity/safety constraints."

            return response.text

        except Exception as e:
            print(f"Gemini API Error: {str(e)}")
            return f"Neural Core Error: System was unable to synthesize a response. ({str(e)})"
