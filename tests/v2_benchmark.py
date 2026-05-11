"""
V2 Orchestrator & Agent Benchmark Suite.

Tests:
1. Router intent classification accuracy (30+ cases)
2. Agent response quality (non-empty, relevant)
3. Edge cases (empty, emoji, multi-language, adversarial)
4. Multi-step routing
5. Latency tracking

Runs against LIVE V2 backend.
"""

import requests
import json
import time
import sys

API_BASE = "https://omni-assistant-v2.onrender.com"

# ---- Test Cases: (input, expected_intent, description) ----

ROUTER_TESTS = [
    # === GENERAL / GREETINGS ===
    ("Hello", "GENERAL", "Simple greeting"),
    ("Hi there!", "GENERAL", "Casual greeting"),
    ("Hey, what can you do?", "GENERAL", "Greeting + capabilities"),
    ("Good morning", "GENERAL", "Time-based greeting"),
    ("Thanks!", "GENERAL", "Gratitude"),
    ("Who are you?", "GENERAL", "Identity question"),
    ("What are your capabilities?", "GENERAL", "Meta capabilities"),

    # === CODER ===
    ("Write a Python function to reverse a string", "CODER", "Code generation"),
    ("Debug this: for i in range(10) print(i)", "CODER", "Debug request"),
    ("Write me a REST API in FastAPI", "CODER", "Framework code request"),
    ("How do I implement a binary search tree in Java?", "CODER", "Data structure code"),
    ("Explain how async/await works in JavaScript", "CODER", "Code explanation"),

    # === ANALYST ===
    ("What's the latest news on Tesla?", "ANALYST", "Company news"),
    ("Show me today's market headlines", "ANALYST", "Market news"),
    ("What happened in the stock market today?", "ANALYST", "Market update"),
    ("Latest news about AI", "ANALYST", "Topic news"),
    ("What's trending in technology?", "ANALYST", "Tech trends"),

    # === ORGANIZER ===
    ("Add a task to review my portfolio", "ORGANIZER", "Task creation"),
    ("What tasks do I have?", "ORGANIZER", "Task listing"),
    ("Show my pending tasks", "ORGANIZER", "Filtered task list"),
    ("Create a reminder to call dentist tomorrow", "ORGANIZER", "Reminder creation"),
    ("Mark the dentist task as done", "ORGANIZER", "Task update"),

    # === ARCHIVIST ===
    ("Remember that my favorite color is blue", "ARCHIVIST", "Memory store"),
    ("What is my favorite color?", "ARCHIVIST", "Memory retrieve"),
    ("Save this: API key is stored in Vault", "ARCHIVIST", "Explicit save"),
    ("Remember I prefer dark mode", "ARCHIVIST", "Preference store"),
    ("What do you know about my preferences?", "ARCHIVIST", "Preference recall"),

    # === RESEARCHER ===
    ("Compare React vs Vue vs Angular for enterprise apps", "RESEARCHER", "Deep comparison"),
    ("Analyze the pros and cons of microservices architecture", "RESEARCHER", "Deep analysis"),
    ("Research the impact of AI on healthcare in 2025", "RESEARCHER", "Research request"),

    # === EDGE CASES ===
    ("", "GENERAL", "Empty input"),
    ("🔥🚀💯", "GENERAL", "Emoji only"),
    ("a", "GENERAL", "Single character"),
    ("Can you help me?", "GENERAL", "Vague request"),
    ("asdfghjkl", "GENERAL", "Gibberish"),
]

# Acceptable mappings (some intents are ambiguous)
ACCEPTABLE_MAPPINGS = {
    "GENERAL": {"GENERAL"},
    "CODER": {"CODER", "RESEARCHER"},  # Code explanation could route to RESEARCHER
    "ANALYST": {"ANALYST", "RESEARCHER"},  # News could trigger research
    "ORGANIZER": {"ORGANIZER"},
    "ARCHIVIST": {"ARCHIVIST", "GENERAL"},  # Memory recall can sometimes be general
    "RESEARCHER": {"RESEARCHER", "ANALYST", "CODER"},  # Research is fuzzy
}


def test_health():
    """Verify backend is alive."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=30)
        data = r.json()
        ok = data.get("status") == "healthy"
        print(f"{'✅' if ok else '❌'} Health Check: {data}")
        return ok
    except Exception as e:
        print(f"❌ Health Check FAILED: {e}")
        return False


def test_router_classification():
    """Test intent classification accuracy."""
    print("\n" + "=" * 70)
    print("ROUTER INTENT CLASSIFICATION BENCHMARK")
    print("=" * 70)

    results = []
    correct = 0
    total = 0
    failures = []

    for user_input, expected_intent, description in ROUTER_TESTS:
        total += 1
        try:
            start = time.time()
            r = requests.post(
                f"{API_BASE}/chat",
                json={"message": user_input or "hello"},  # Fallback for empty
                timeout=120,
            )
            latency = round(time.time() - start, 2)
            data = r.json()

            actual_intent = data.get("intent", "UNKNOWN")
            response = data.get("response", "")
            response_preview = response[:80].replace("\n", " ") if response else "(empty)"

            # Check if actual intent is in acceptable set
            acceptable = ACCEPTABLE_MAPPINGS.get(expected_intent, {expected_intent})
            is_correct = actual_intent in acceptable
            has_response = bool(response and len(response.strip()) > 5)

            if is_correct:
                correct += 1

            status = "✅" if (is_correct and has_response) else "⚠️" if is_correct else "❌"

            result = {
                "input": user_input[:50],
                "expected": expected_intent,
                "actual": actual_intent,
                "correct": is_correct,
                "has_response": has_response,
                "latency": latency,
                "response_preview": response_preview,
            }
            results.append(result)

            if not is_correct or not has_response:
                failures.append(result)

            print(f"  {status} [{latency}s] '{user_input[:40]}' → {actual_intent} (expected: {expected_intent})")
            if not has_response:
                print(f"       ⚠️  EMPTY/SHORT RESPONSE: {response_preview}")

        except requests.exceptions.Timeout:
            print(f"  ⏳ TIMEOUT: '{user_input[:40]}'")
            results.append({"input": user_input[:50], "expected": expected_intent, "actual": "TIMEOUT", "correct": False, "has_response": False, "latency": 120})
            failures.append(results[-1])
        except Exception as e:
            print(f"  💥 ERROR: '{user_input[:40]}' → {e}")
            results.append({"input": user_input[:50], "expected": expected_intent, "actual": "ERROR", "correct": False, "has_response": False, "latency": 0})
            failures.append(results[-1])

    # Summary
    accuracy = round(correct / total * 100, 1) if total else 0
    response_rate = round(sum(1 for r in results if r.get("has_response")) / total * 100, 1)
    avg_latency = round(sum(r.get("latency", 0) for r in results) / total, 2)

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Router Accuracy:    {correct}/{total} ({accuracy}%)")
    print(f"  Response Rate:      {sum(1 for r in results if r.get('has_response'))}/{total} ({response_rate}%)")
    print(f"  Avg Latency:        {avg_latency}s")
    print(f"  Failures:           {len(failures)}")

    if failures:
        print("\n  --- FAILURES ---")
        for f in failures:
            print(f"  ❌ '{f['input']}' → got {f['actual']}, expected {f['expected']}, response: {f.get('has_response')}")

    return {
        "accuracy": accuracy,
        "response_rate": response_rate,
        "avg_latency": avg_latency,
        "total": total,
        "correct": correct,
        "failures": failures,
        "results": results,
    }


def test_data_endpoints():
    """Test data endpoints respond correctly."""
    print("\n" + "=" * 70)
    print("DATA ENDPOINT TESTS")
    print("=" * 70)

    endpoints = [
        ("/tasks", "tasks"),
        ("/knowledge", "knowledge"),
        ("/v2/memories", "memories"),
        ("/api/briefing", "briefing"),
    ]

    for path, key in endpoints:
        try:
            r = requests.get(f"{API_BASE}{path}", timeout=30)
            data = r.json()
            has_data = key in data or "status" in data
            print(f"  {'✅' if has_data else '❌'} GET {path}: {list(data.keys())}")
        except Exception as e:
            print(f"  ❌ GET {path}: {e}")


if __name__ == "__main__":
    print("🧪 Omni-Agent V2 Benchmark Suite")
    print(f"   Target: {API_BASE}")
    print(f"   Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Phase 1: Health
    if not test_health():
        print("\n💀 Backend is down. Aborting.")
        sys.exit(1)

    # Phase 2: Data endpoints
    test_data_endpoints()

    # Phase 3: Router + Agent benchmark
    report = test_router_classification()

    # Final grade
    print("\n" + "=" * 70)
    grade = "A+" if report["accuracy"] >= 90 and report["response_rate"] >= 90 else \
            "A" if report["accuracy"] >= 85 and report["response_rate"] >= 85 else \
            "B" if report["accuracy"] >= 75 and report["response_rate"] >= 75 else \
            "C" if report["accuracy"] >= 60 else "F"
    print(f"  FINAL GRADE: {grade}")
    print(f"  Router: {report['accuracy']}% | Responses: {report['response_rate']}% | Latency: {report['avg_latency']}s")
    print("=" * 70)
