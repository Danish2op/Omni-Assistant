"""
TDD Tests for Communicator Agent — Routine Scheduling Fix.

Bug: create_routine() used wrong column names (contact_email, content_params, time)
     that don't exist in the Supabase 'routines' table, causing PGRST204 errors.

These tests hit the REAL Supabase database — they are integration tests
because the entire bug was a schema mismatch with the live DB.
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

# Skip entire module if Supabase creds are missing (CI without secrets)
pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"),
    reason="Supabase credentials not configured",
)


# ---- Fixtures ----

@pytest.fixture
def db():
    """Real Supabase client."""
    from app.core.database_v2 import SupabaseV2Client
    return SupabaseV2Client()


@pytest.fixture
def agent():
    """Real V2EmailerAgent (uses real DB, mocks nothing)."""
    from app.agents.v2_emailer import V2EmailerAgent
    return V2EmailerAgent()


@pytest.fixture
def cleanup_routine(db):
    """Auto-cleanup: collects routine IDs and deletes them after the test."""
    created_ids = []
    yield created_ids
    for rid in created_ids:
        db.delete_data("routines", {"id": rid})


# ---- TEST 1: create_routine saves to Supabase and returns True ----

def test_create_routine_saves_successfully(agent, db, cleanup_routine):
    """create_routine should return True and persist a row in the routines table."""
    success = agent.create_routine(
        contact_email="tdd-test@example.com",
        routine_type="goodnight_email",
        frequency="daily",
        schedule_time="21:00",
        content_params={"query": "send good night email"},
    )

    assert success is True, "create_routine must return True on successful save"

    # Verify the row actually exists in the DB
    rows = db.get_data("routines", {"recipient_email": "tdd-test@example.com"})
    assert len(rows) >= 1, "Routine row must exist in Supabase after create_routine"
    cleanup_routine.extend([r["id"] for r in rows])


# ---- TEST 2: saved routine uses correct column names ----

def test_routine_uses_correct_column_names(agent, db, cleanup_routine):
    """The saved row must use 'recipient_email' and 'parameters', NOT the old names."""
    agent.create_routine(
        contact_email="schema-test@example.com",
        routine_type="daily_quote",
        frequency="daily",
        schedule_time="09:00",
        content_params={"topic": "motivation"},
    )

    rows = db.get_data("routines", {"recipient_email": "schema-test@example.com"})
    assert len(rows) >= 1, "Row must be queryable by recipient_email"
    row = rows[0]
    cleanup_routine.extend([r["id"] for r in rows])

    # Column correctness
    assert row["recipient_email"] == "schema-test@example.com"
    assert row["type"] == "daily_quote"
    assert row["frequency"] == "daily"
    assert row["status"] == "active"

    # schedule_time must be inside 'parameters' JSONB, not a top-level 'time' column
    assert isinstance(row["parameters"], dict), "parameters must be a JSONB dict"
    assert row["parameters"]["schedule_time"] == "09:00"
    assert row["parameters"]["topic"] == "motivation"


# ---- TEST 3: _extract_json handles messy LLM output ----

def test_extract_json_from_clean_output(agent):
    """_extract_json should extract JSON from a clean LLM response."""
    raw = '{"routine_type": "email", "frequency": "daily", "time": "09:00"}'
    result = agent._extract_json(raw)
    assert result is not None
    import json
    parsed = json.loads(result)
    assert parsed["routine_type"] == "email"


def test_extract_json_from_markdown_wrapped(agent):
    """_extract_json should handle JSON wrapped in markdown code fences."""
    raw = '```json\n{"routine_type": "email", "frequency": "daily"}\n```'
    result = agent._extract_json(raw)
    assert result is not None
    import json
    parsed = json.loads(result)
    assert parsed["frequency"] == "daily"


def test_extract_json_from_chatty_llm(agent):
    """_extract_json should extract JSON buried in conversational text."""
    raw = 'Sure! Here is your result:\n{"type": "reminder", "time": "10:00"}\nHope that helps!'
    result = agent._extract_json(raw)
    assert result is not None
    import json
    parsed = json.loads(result)
    assert parsed["type"] == "reminder"


def test_extract_json_returns_none_for_garbage(agent):
    """_extract_json should return None when there's no JSON at all."""
    raw = "I'm sorry, I can't help with that right now."
    result = agent._extract_json(raw)
    assert result is None


# ---- TEST 4: database error logging is verbose ----

def test_db_error_logging_captures_details(db, capsys):
    """_handle_connection_error should print the full exception details for non-pause errors."""
    fake_error = Exception("Could not find the 'contact_email' column of 'routines' in the schema cache")
    db._handle_connection_error(fake_error, "save_data(routines)")

    captured = capsys.readouterr()
    assert "save_data(routines)" in captured.out
    assert "contact_email" in captured.out
    assert "Full Exception Details" in captured.out
