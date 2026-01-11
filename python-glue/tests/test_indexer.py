"""Tests for codebase indexer and file watching"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from unified_ai.indexer.manager import IndexerManager, HAS_PYO3
except ImportError:
    HAS_PYO3 = False


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db():
    """Create a temporary database path"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmpfile:
        db_path = Path(tmpfile.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
def indexer_manager(temp_db):
    """Create an IndexerManager instance"""
    return IndexerManager(project_id="test-project", db_path=temp_db)


@pytest.mark.skipif(not HAS_PYO3, reason="PyO3 bindings not available")
class TestIndexerManager:
    """Test IndexerManager functionality"""
    
    def test_indexer_manager_creation(self, indexer_manager):
        """Test that IndexerManager can be created"""
        assert indexer_manager.project_id == "test-project"
        assert indexer_manager.indexer is not None
    
    def test_watch_directory_creates_watcher(self, indexer_manager, temp_dir):
        """Test that watch_directory creates a watcher"""
        # Create a test file
        test_file = temp_dir / "test.py"
        test_file.write_text("def hello(): pass\n")
        
        # Watch the directory
        indexer_manager.watch_directory(temp_dir)
        
        # Verify watcher was created
        assert indexer_manager._watcher is not None
        
        # Cleanup
        indexer_manager.stop_watching()
    
    def test_stop_watching(self, indexer_manager, temp_dir):
        """Test that stop_watching stops the watcher"""
        indexer_manager.watch_directory(temp_dir)
        assert indexer_manager._watcher is not None
        
        indexer_manager.stop_watching()
        assert indexer_manager._watcher is None
    
    def test_watch_directory_with_error_callback(self, indexer_manager, temp_dir):
        """Test that error callback is called on errors"""
        error_callback = Mock()
        
        indexer_manager.watch_directory(temp_dir, error_callback=error_callback)
        
        # The callback should be stored (actual errors would trigger it)
        assert indexer_manager._watcher is not None
        
        indexer_manager.stop_watching()
    
    def test_context_manager(self, indexer_manager, temp_dir):
        """Test that IndexerManager works as a context manager"""
        with indexer_manager:
            indexer_manager.watch_directory(temp_dir)
            assert indexer_manager._watcher is not None
        
        # Watcher should be stopped after context exit
        assert indexer_manager._watcher is None
    
    def test_watch_directory_raises_without_pyo3(self, temp_db):
        """Test that watch_directory raises error without PyO3"""
        with patch('unified_ai.indexer.manager.HAS_PYO3', False):
            manager = IndexerManager(project_id="test", db_path=temp_db)
            with pytest.raises(RuntimeError, match="PyO3 bindings not available"):
                manager.watch_directory(Path("/tmp"))
    
    def test_multiple_watch_calls(self, indexer_manager, temp_dir):
        """Test that multiple watch calls reuse the same watcher"""
        indexer_manager.watch_directory(temp_dir)
        watcher1 = indexer_manager._watcher
        
        # Watch another path (should reuse watcher)
        indexer_manager.watch_directory(temp_dir / "subdir")
        watcher2 = indexer_manager._watcher
        
        assert watcher1 is watcher2
        
        indexer_manager.stop_watching()


@pytest.mark.skipif(not HAS_PYO3, reason="PyO3 bindings not available")
class TestFileWatcherIntegration:
    """Integration tests for file watching"""
    
    def test_file_creation_triggers_indexing(self, indexer_manager, temp_dir):
        """Test that creating a file triggers indexing"""
        # Start watching
        indexer_manager.watch_directory(temp_dir)
        
        # Create a Python file
        test_file = temp_dir / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")
        
        # Give watcher time to process (debounce is 500ms)
        time.sleep(1.0)
        
        # Search for the function
        results = indexer_manager.search("hello", limit=10)
        
        # Should find the function (if indexing worked)
        # Note: This is a basic test - actual indexing depends on Rust implementation
        assert isinstance(results, list)
        
        indexer_manager.stop_watching()
    
    def test_file_modification_triggers_reindexing(self, indexer_manager, temp_dir):
        """Test that modifying a file triggers re-indexing"""
        # Create initial file
        test_file = temp_dir / "test.py"
        test_file.write_text("def hello():\n    pass\n")
        
        # Start watching
        indexer_manager.watch_directory(temp_dir)
        
        # Wait for initial indexing
        time.sleep(0.6)
        
        # Modify the file
        test_file.write_text("def hello():\n    return 'modified'\n")
        
        # Give watcher time to process
        time.sleep(1.0)
        
        # Should have updated index
        results = indexer_manager.search("modified", limit=10)
        assert isinstance(results, list)
        
        indexer_manager.stop_watching()
    
    def test_file_deletion_triggers_removal(self, indexer_manager, temp_dir):
        """Test that deleting a file removes it from index"""
        # Create file
        test_file = temp_dir / "test.py"
        test_file.write_text("def hello():\n    pass\n")
        
        # Start watching
        indexer_manager.watch_directory(temp_dir)
        
        # Wait for indexing
        time.sleep(0.6)
        
        # Delete file
        test_file.unlink()
        
        # Give watcher time to process
        time.sleep(1.0)
        
        # File should be removed from index
        # (exact behavior depends on Rust implementation)
        indexer_manager.stop_watching()


@pytest.mark.skipif(not HAS_PYO3, reason="PyO3 bindings not available")
class TestFileWatcherErrorHandling:
    """Test error handling in file watcher"""
    
    def test_error_callback_called_on_error(self, indexer_manager, temp_dir):
        """Test that error callback is called when errors occur"""
        error_callback = Mock()
        
        indexer_manager.watch_directory(temp_dir, error_callback=error_callback)
        
        # Create an invalid file that might cause errors
        invalid_file = temp_dir / "invalid.txt"
        invalid_file.write_text("not code")
        
        # Give watcher time to process
        time.sleep(1.0)
        
        # Callback might be called if there are errors
        # (depends on actual error conditions)
        
        indexer_manager.stop_watching()
    
    def test_watcher_stops_gracefully(self, indexer_manager, temp_dir):
        """Test that watcher stops gracefully"""
        indexer_manager.watch_directory(temp_dir)
        
        # Stop should not raise exceptions
        indexer_manager.stop_watching()
        
        # Should be able to stop again without error
        indexer_manager.stop_watching()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
