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
        Generate a text response from Gemini 2.0 Flash.

        Args:
            prompt: The user's input text.
            system_instruction: Optional system-level instruction to guide the model.

        Returns:
            The generated text response as a string.
        """
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        response = self.client.models.generate_content(
            model="models/gemini-flash-lite-latest",
            contents=prompt,
            config=config
        )

        return response.text
