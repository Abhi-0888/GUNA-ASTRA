import pytest


def test_imports():
    try:
        import agents.system_agent
        import core.intent_engine
        import core.orchestrator
        import utils.logger

        # Test passed if we got here without ImportError
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
