
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock environment variables for testing
os.environ["OPENROUTER_API_KEY"] = "mock_key"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock_key"
os.environ["RESEND_API_KEY"] = "mock_key"
os.environ["USER_EMAIL"] = "danish@example.com"

# Import after path setup
from app.agents.v2_router import V2RouterAgent
from app.agents.v2_emailer import V2EmailerAgent

@pytest.fixture
def mock_clients():
    # Patch where they are USED in the agents
    with patch('app.agents.v2_emailer.MultiModelClient') as mock_llm_cls, \
         patch('app.agents.v2_emailer.SupabaseV2Client') as mock_db_cls, \
         patch('app.agents.v2_emailer.ResendTool') as mock_resend_cls:
        
        mock_llm = mock_llm_cls.return_value
        mock_db = mock_db_cls.return_value
        mock_resend = mock_resend_cls.return_value
        
        # Setup mock behavior
        mock_db.save_data.return_value = {"id": "mock_id"}
        mock_db.get_data.return_value = []
        mock_db.search_data.return_value = []
        mock_db.is_paused = False # Ensure it's not paused by default in tests
        
        yield {
            "llm": mock_llm,
            "db": mock_db,
            "resend": mock_resend
        }

def test_router_heuristics():
    # Router uses MultiModelClient too, but for heuristics it might not hit LLM
    with patch('app.agents.v2_router.MultiModelClient'):
        router = V2RouterAgent()
        
        test_cases = [
            ("everyday at 9 am email me the daily leetcode question link", "SCHEDULE"),
            ("every monday morning send me a summary", "SCHEDULE"),
            ("remind me in 5 minutes to take a break", "REMIND"),
            ("email to paryag about the meeting", "EMAIL"),
            ("save this password for ssh: 12345", "STORE"),
            ("what is my ssh password", "RETRIEVE"),
        ]
        
        for query, expected_action in test_cases:
            plan = router.route_request(query)
            assert plan['tasks'][0]['action'] == expected_action

def test_emailer_schedule_logic(mock_clients):
    emailer = V2EmailerAgent()
    query = "everyday at 9 am email me the daily leetcode question link"
    
    response = emailer.handle_query(query, action="SCHEDULE")
    assert "Scheduled" in response
    assert "daily" in response
    assert "9 AM" in response

def test_emailer_reminder_logic(mock_clients):
    emailer = V2EmailerAgent()
    query = "remind me in 5 minutes to take a break"
    
    # Mock LLM extraction for reminder
    mock_clients['llm'].generate.return_value = '{"message": "take a break", "wait_minutes": 5}'
    
    response = emailer.handle_query(query, action="REMIND")
    assert "Set a reminder for 5 minutes" in response
