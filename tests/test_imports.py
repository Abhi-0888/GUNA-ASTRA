import pytest

def test_imports():
    try:
        import core.orchestrator
        import core.intent_engine
        import agents.system_agent
        import utils.logger
        
        # Test passed if we got here without ImportError
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
