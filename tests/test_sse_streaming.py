"""
SSE Streaming Tests — GREEN phase.

Tests:
1. generate_stream() yields str chunks (requires OPENROUTER_API_KEY)
2. /chat/stream returns text/event-stream
3. SSE events have correct format: data: {...}\n\n
4. Final event has [DONE] marker
"""

import os
import pytest
import json
import requests

API_BASE = "https://omni-assistant-v2.onrender.com"
HAS_API_KEY = bool(os.environ.get("OPENROUTER_API_KEY"))


class TestGenerateStream:
    """Test MultiModelClient.generate_stream() yields chunks."""

    def test_generate_stream_exists(self):
        """generate_stream method must exist on MultiModelClient."""
        # Mock env to avoid ValueError
        original = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = original or "test-key"
        try:
            from app.core.llm_v2 import MultiModelClient
            client = MultiModelClient()
            assert hasattr(client, "generate_stream"), "generate_stream() missing"
        finally:
            if original is None:
                del os.environ["OPENROUTER_API_KEY"]

    @pytest.mark.skipif(not HAS_API_KEY, reason="OPENROUTER_API_KEY not set")
    def test_generate_stream_yields_strings(self):
        """generate_stream must yield string chunks."""
        from app.core.llm_v2 import MultiModelClient, AgentRole
        client = MultiModelClient()
        chunks = list(client.generate_stream(
            prompt="Say hello in one word.",
            role=AgentRole.GENERALIST,
            max_tokens=20,
        ))
        assert len(chunks) > 0, "No chunks yielded"
        assert all(isinstance(c, str) for c in chunks), "Chunks must be strings"
        combined = "".join(chunks)
        assert len(combined.strip()) > 0, "Combined output empty"


class TestSSEEndpoint:
    """Test /chat/stream endpoint returns proper SSE (hits live Render)."""

    def test_stream_endpoint_exists(self):
        """POST /chat/stream must not 404."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Hello"},
                          stream=True, timeout=120)
        assert r.status_code != 404, f"/chat/stream returned 404"
        assert r.status_code == 200, f"Got {r.status_code}"

    def test_stream_content_type(self):
        """Response must be text/event-stream."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Hello"},
                          stream=True, timeout=120)
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"Content-Type: {ct}"

    def test_stream_events_format(self):
        """Each SSE event must be 'data: {json}\\n\\n'."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Hi"},
                          stream=True, timeout=120)

        events = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                payload = line[6:]
                if payload == "[DONE]":
                    events.append({"type": "DONE"})
                    break
                parsed = json.loads(payload)
                events.append(parsed)

        assert len(events) >= 2, f"Expected >=2 events, got {len(events)}"
        assert events[0].get("type") == "ROUTER", f"First event: {events[0]}"
        assert events[-1].get("type") == "DONE", "Missing [DONE] marker"

    def test_stream_has_text_chunks(self):
        """Must have TEXT-type events with actual content."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Say hello"},
                          stream=True, timeout=120)

        text_chunks = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: ") and line[6:] != "[DONE]":
                parsed = json.loads(line[6:])
                if parsed.get("type") == "TEXT":
                    text_chunks.append(parsed.get("content", ""))

        combined = "".join(text_chunks)
        assert len(combined.strip()) > 0, "No text content streamed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
