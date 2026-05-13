import pytest
import os
from unittest.mock import patch
from app.core.llm_v2 import AgentRole, MultiModelClient

def test_communicator_role_exists():
    # This will now pass as COMMUNICATOR is added to AgentRole
    assert hasattr(AgentRole, "COMMUNICATOR")

@patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-key"})
def test_communicator_model_routing():
    # This will now pass as MODEL_REGISTRY is updated
    client = MultiModelClient()
    model = client.get_model_for_role(AgentRole.COMMUNICATOR)
    assert model == "meta-llama/llama-3.3-70b-instruct:free"
