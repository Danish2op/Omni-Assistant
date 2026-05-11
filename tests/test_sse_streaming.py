"""
SSE Streaming Tests — RED phase.

Tests:
1. generate_stream() yields str chunks
2. /chat/stream returns text/event-stream
3. SSE events have correct format: data: {...}\n\n
4. Final event has [DONE] marker
"""

import pytest
import json
import requests

API_BASE = "https://omni-assistant-v2.onrender.com"


class TestGenerateStream:
    """Test MultiModelClient.generate_stream() yields chunks."""

    def test_generate_stream_exists(self):
        """generate_stream method must exist on MultiModelClient."""
        from app.core.llm_v2 import MultiModelClient
        client = MultiModelClient()
        assert hasattr(client, "generate_stream"), "generate_stream() missing"

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
    """Test /chat/stream endpoint returns proper SSE."""

    def test_stream_endpoint_exists(self):
        """GET /chat/stream must not 404."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Hello"},
                          stream=True, timeout=60)
        assert r.status_code != 404, f"/chat/stream returned 404"
        assert r.status_code == 200, f"Got {r.status_code}"

    def test_stream_content_type(self):
        """Response must be text/event-stream."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Hello"},
                          stream=True, timeout=60)
        ct = r.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"Content-Type: {ct}"

    def test_stream_events_format(self):
        """Each SSE event must be 'data: {json}\n\n'."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Hi"},
                          stream=True, timeout=60)

        events = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                payload = line[6:]  # strip "data: "
                if payload == "[DONE]":
                    events.append({"type": "DONE"})
                    break
                parsed = json.loads(payload)
                events.append(parsed)

        assert len(events) >= 2, f"Expected >=2 events, got {len(events)}"

        # First event should be ROUTER type
        assert events[0].get("type") == "ROUTER", f"First event: {events[0]}"

        # Last event should be DONE
        assert events[-1].get("type") == "DONE", "Missing [DONE] marker"

    def test_stream_has_text_chunks(self):
        """Must have TEXT-type events with actual content."""
        r = requests.post(f"{API_BASE}/chat/stream",
                          json={"message": "Say hello"},
                          stream=True, timeout=60)

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
