"""Basic smoke tests that don't require external dependencies"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported"""
    try:
        from unified_ai import adapters
        from unified_ai import config
        from unified_ai import resilience
        from unified_ai import observability
        from unified_ai import cost
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_resilience_basic():
    """Test basic resilience functionality"""
    try:
        from unified_ai.resilience import RetryPolicy, ExponentialBackoffRetry
        
        policy = ExponentialBackoffRetry(max_attempts=3, initial_delay=0.1)
        assert policy.max_attempts == 3
        assert policy.should_retry(1, ConnectionError()) is True
        assert policy.should_retry(3, ConnectionError()) is False
        
        print("✓ Resilience tests passed")
        return True
    except Exception as e:
        print(f"✗ Resilience test failed: {e}")
        return False


def test_config_basic():
    """Test configuration loading"""
    try:
        from unified_ai.config import Config, load_config
        
        # Test default config
        config = Config()
        assert config.routing.default_tool == "claude"
        assert isinstance(config.tools, dict)
        
        print("✓ Config tests passed")
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False


def test_router_basic():
    """Test router basic functionality"""
    try:
        from unified_ai.router import Router
        
        routing_rules = {
            "code_editing": ["claude"],
            "research": ["perplexity"],
            "general_chat": ["claude", "gpt"],
        }
        router = Router(routing_rules, "claude")
        
        decision = router.route("Hello", explicit_tool="gpt")
        assert decision["selected_tools"] == ["gpt"]
        
        decision2 = router.route("Refactor this code")
        assert len(decision2["selected_tools"]) > 0
        
        print("✓ Router tests passed")
        return True
    except Exception as e:
        print(f"✗ Router test failed: {e}")
        return False


def run_basic_tests():
    """Run all basic tests"""
    print("Running basic smoke tests...\n")
    
    tests = [
        test_imports,
        test_resilience_basic,
        test_config_basic,
        test_router_basic,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{total}")
    print(f"{'='*50}")
    
    return passed == total


if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)
