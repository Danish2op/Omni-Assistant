"""
TDD Tests for Reminder Feature.

Bugs found:
  1. scheduler_instance is never started in main_v2.py lifespan — jobs added but never fire.
  2. USER_EMAIL not set — reminder sends to fake "danishsharma@example.com".
  3. _handle_reminder calls async_send_routine_email (async) but needs sync wrapper for date trigger.

These tests verify the reminder pipeline works correctly.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"),
    reason="Supabase credentials not configured",
)


# ---- TEST 1: Scheduler must be started in lifespan ----

def test_scheduler_instance_is_started_in_lifespan():
    """The V2 scheduler_instance must be started during app lifespan, not just the news scheduler."""
    import importlib
    import app.core.scheduler_v2 as sched_mod
    # Re-read main_v2.py source to verify scheduler_instance.start() is called
    main_v2_path = os.path.join(os.path.dirname(__file__), "..", "main_v2.py")
    with open(main_v2_path) as f:
        source = f.read()

    assert "scheduler_instance.start()" in source, (
        "main_v2.py lifespan must call scheduler_instance.start() "
        "so reminder/routine jobs actually fire"
    )


# ---- TEST 2: _handle_reminder resolves user email properly ----

def test_reminder_uses_user_email_env_var():
    """_handle_reminder should use USER_EMAIL env var when set."""
    from app.agents.v2_emailer import V2EmailerAgent

    agent = V2EmailerAgent()

    with patch.dict(os.environ, {"USER_EMAIL": "danish@danis.live"}):
        with patch.object(agent, 'get_contact', return_value=None):
            with patch.object(agent.llm, 'generate', return_value='{"message": "turn off lights", "wait_minutes": 5, "absolute_time": null}'):
                with patch.object(agent, '_schedule_reminder_job') as mock_schedule:
                    result = agent._handle_reminder("remind me to turn off lights in 5 minutes")

    mock_schedule.assert_called_once()
    call_args = mock_schedule.call_args
    assert call_args[0][0] == "danish@danis.live", f"Expected danish@danis.live, got {call_args[0][0]}"


def test_reminder_falls_back_to_self_contact():
    """_handle_reminder should fall back to 'self' contact from DB when USER_EMAIL is unset."""
    from app.agents.v2_emailer import V2EmailerAgent

    agent = V2EmailerAgent()

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("USER_EMAIL", None)
        with patch.object(agent, 'get_contact', return_value={"email": "me@danis.live"}):
            with patch.object(agent.llm, 'generate', return_value='{"message": "turn off lights", "wait_minutes": 5, "absolute_time": null}'):
                with patch.object(agent, '_schedule_reminder_job') as mock_schedule:
                    result = agent._handle_reminder("remind me to turn off lights in 5 minutes")

    mock_schedule.assert_called_once()
    call_args = mock_schedule.call_args
    assert call_args[0][0] == "me@danis.live"


# ---- TEST 3: _handle_reminder schedules a job with correct delay ----

def test_reminder_schedules_job_with_correct_minutes():
    """_handle_reminder should schedule a job for the correct number of minutes in the future."""
    from app.agents.v2_emailer import V2EmailerAgent

    agent = V2EmailerAgent()

    with patch.dict(os.environ, {"USER_EMAIL": "test@test.com"}):
        with patch.object(agent, 'get_contact', return_value=None):
            with patch.object(agent.llm, 'generate', return_value='{"message": "turn off lights", "wait_minutes": 5, "absolute_time": null}'):
                with patch.object(agent, '_schedule_reminder_job') as mock_schedule:
                    result = agent._handle_reminder("remind me to turn off lights in 5 minutes")

    assert "5 minutes" in result
    mock_schedule.assert_called_once()
    # Verify args: (email, subject, html, wait_minutes)
    args = mock_schedule.call_args[0]
    assert args[0] == "test@test.com"
    assert args[3] == 5  # wait_minutes


# ---- TEST 4: _handle_reminder returns friendly message on LLM failure ----

def test_reminder_handles_llm_garbage():
    """_handle_reminder should return a friendly message when the LLM produces garbage."""
    from app.agents.v2_emailer import V2EmailerAgent

    agent = V2EmailerAgent()

    with patch.object(agent.llm, 'generate', return_value="Sorry, I can't process that right now."):
        result = agent._handle_reminder("remind me about something")

    assert "trouble" in result.lower() or "try" in result.lower()


# ---- TEST 5: scheduler_instance shutdown in lifespan ----

def test_scheduler_instance_shutdown_in_lifespan():
    """The V2 scheduler_instance must be shut down during app shutdown."""
    main_v2_path = os.path.join(os.path.dirname(__file__), "..", "main_v2.py")
    with open(main_v2_path) as f:
        source = f.read()

    assert "scheduler_instance.shutdown()" in source, (
        "main_v2.py lifespan must call scheduler_instance.shutdown() on app exit"
    )
