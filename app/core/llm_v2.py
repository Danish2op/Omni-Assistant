"""
V2 Multi-Model LLM Client for Omni-Agent.

Routes requests to specialized models based on agent role.
Each role has its own fallback cascade of free OpenRouter models.
"""

import os
import json
import requests
from enum import Enum
from typing import Optional, Generator


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class AgentRole(Enum):
    """Defines specialized roles for multi-model routing."""
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    RESEARCHER = "researcher"
    GENERALIST = "generalist"


# Per-role fallback cascades — all free-tier models
MODEL_REGISTRY = {
    AgentRole.ORCHESTRATOR: [
        "google/gemma-4-26b-a4b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-001",
    ],
    AgentRole.CODER: [
        "qwen/qwen3-coder:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "google/gemini-2.0-flash-001",
    ],
    AgentRole.RESEARCHER: [
        "deepseek/deepseek-r1:free",
        "qwen/qwq-32b:free",
        "google/gemini-2.0-flash-001",
    ],
    AgentRole.GENERALIST: [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-26b-a4b-it:free",
        "google/gemini-2.0-flash-001",
    ],
}


class MultiModelClient:
    """
    V2 LLM client with per-role model routing and automatic fallback.

    Usage:
        client = MultiModelClient()
        response = client.generate(
            prompt="classify this intent",
            system_instruction="You are the orchestrator.",
            role=AgentRole.ORCHESTRATOR
        )
    """

    def __init__(self):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found.")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://omni-agent-v2.app",
            "X-Title": "Omni-Agent V2",
        }

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        role: AgentRole = AgentRole.GENERALIST,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate response using role-specific model with fallback cascade.

        Args:
            prompt: User/agent prompt.
            system_instruction: System prompt for behavior control.
            role: AgentRole determining which model cascade to use.
            max_tokens: Max output tokens.
            temperature: Sampling temperature.

        Returns:
            Generated text or error message string.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        fallback_chain = MODEL_REGISTRY.get(role, MODEL_REGISTRY[AgentRole.GENERALIST])
        last_error = None

        for model_id in fallback_chain:
            try:
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }

                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=45,
                )

                # Rate limit or unavailable -> try next model
                if response.status_code in (429, 503):
                    print(f"[V2 LLM] {model_id} rate-limited/unavailable, falling back...")
                    last_error = f"HTTP {response.status_code}"
                    continue

                if response.status_code != 200:
                    error_msg = response.text[:200]
                    print(f"[V2 LLM] {model_id} error: {response.status_code} - {error_msg}")
                    last_error = f"HTTP {response.status_code}: {error_msg}"
                    continue

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    print(f"[V2 LLM] {model_id} returned empty choices.")
                    last_error = "Empty choices"
                    continue

                text = choices[0].get("message", {}).get("content", "")
                if not text:
                    last_error = "Empty content"
                    continue

                return text

            except requests.exceptions.Timeout:
                print(f"[V2 LLM] {model_id} timeout, falling back...")
                last_error = "Timeout"
                continue
            except Exception as e:
                last_error = str(e)
                print(f"[V2 LLM] {model_id} exception: {last_error}")
                continue

        # All models exhausted
        print(f"[V2 LLM] All {role.value} models exhausted. Last error: {last_error}")
        return f"[V2 Error] All {role.value} models at capacity. Try again shortly."

    def get_model_for_role(self, role: AgentRole) -> str:
        """Return primary model name for a given role (for logging/UI)."""
        chain = MODEL_REGISTRY.get(role, MODEL_REGISTRY[AgentRole.GENERALIST])
        return chain[0] if chain else "unknown"

    def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        role: AgentRole = AgentRole.GENERALIST,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """
        Stream response chunks from OpenRouter.

        Yields text deltas as they arrive. Falls back through model cascade.
        """
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        fallback_chain = MODEL_REGISTRY.get(role, MODEL_REGISTRY[AgentRole.GENERALIST])
        last_error = None

        for model_id in fallback_chain:
            try:
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                }

                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                    stream=True,
                )

                if response.status_code in (429, 503):
                    print(f"[V2 STREAM] {model_id} rate-limited, falling back...")
                    last_error = f"HTTP {response.status_code}"
                    continue

                if response.status_code != 200:
                    print(f"[V2 STREAM] {model_id} error: {response.status_code}")
                    last_error = f"HTTP {response.status_code}"
                    continue

                # Stream SSE chunks from OpenRouter
                yielded_any = False
                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            yielded_any = True
                            yield delta
                    except json.JSONDecodeError:
                        continue

                if yielded_any:
                    return  # Success, stop fallback

                last_error = "No content streamed"
                continue

            except requests.exceptions.Timeout:
                print(f"[V2 STREAM] {model_id} timeout, falling back...")
                last_error = "Timeout"
                continue
            except Exception as e:
                last_error = str(e)
                print(f"[V2 STREAM] {model_id} exception: {last_error}")
                continue

        # All models exhausted
        yield f"[V2 Error] All {role.value} models at capacity."
