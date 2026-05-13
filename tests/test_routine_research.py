import pytest
from unittest.mock import MagicMock, patch
from app.core.jobs_v2 import execute_intelligent_routine

@patch("app.agents.v2_analyst.V2AnalystAgent")
@patch("app.core.llm_v2.MultiModelClient")
@patch("app.core.jobs_v2.ResendTool")
def test_execute_intelligent_routine_triggers_research_for_generic_task(
    mock_resend_class, mock_llm_class, mock_analyst_class
):
    """
    Test that execute_intelligent_routine triggers research for non-news/market routines
    like 'leetcode' if the logic is updated to be generic.
    """
    # Setup mocks
    mock_analyst = mock_analyst_class.return_value
    mock_analyst.handle_query.return_value = "Today's LeetCode question is 123. Two Sum."
    
    mock_llm_inst = mock_llm_class.return_value
    mock_llm_inst.generate.return_value = "Formatted LeetCode content"
    
    mock_resend_inst = mock_resend_class.return_value
    mock_resend_inst.send_email.return_value = True

    # Call the function with a generic routine type
    execute_intelligent_routine(
        to="test@example.com",
        routine_type="leetcode",
        params={"query": "Get daily leetcode question"}
    )

    # Check if Analyst was called
    mock_analyst.handle_query.assert_called_once_with("Get daily leetcode question")
    
    # Check if Resend was called with the formatted content
    mock_resend_inst.send_email.assert_called_once()
    args, kwargs = mock_resend_inst.send_email.call_args
    # The third argument should contain our formatted content
    assert "Formatted LeetCode content" in args[2]
