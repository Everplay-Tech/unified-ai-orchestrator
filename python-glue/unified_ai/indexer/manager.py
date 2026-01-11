"""Indexer manager for Python interface"""

from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from unified_ai_orchestrator.pyo3_bridge import PyCodebaseIndexer, PySemanticSearch
    HAS_PYO3 = True
except ImportError:
    HAS_PYO3 = False


class IndexerManager:
    """Manager for codebase indexing"""
    
    def __init__(self, project_id: str, db_path: Path):
        self.project_id = project_id
        self.db_path = db_path
        
        if HAS_PYO3:
            self.indexer = PyCodebaseIndexer(project_id, str(db_path))
            self.search_engine = PySemanticSearch(str(db_path))
        else:
            self.indexer = None
            self.search_engine = None
    
    def index_directory(self, root_path: Path) -> int:
        """Index a directory recursively"""
        if HAS_PYO3 and self.indexer:
            return self.indexer.index_directory(str(root_path))
        else:
            print("PyO3 bindings not available - indexing not supported")
            return 0
    
    def index_file(self, file_path: Path) -> None:
        """Index a single file"""
        if HAS_PYO3 and self.indexer:
            self.indexer.index_file(str(file_path))
        else:
            print("PyO3 bindings not available - indexing not supported")
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search codebase"""
        if HAS_PYO3 and self.search_engine:
            results = self.search_engine.search(self.project_id, query, limit)
            return [
                {
                    "file_path": file_path,
                    "block_type": block_type,
                    "name": name,
                    "start_line": start_line,
                    "end_line": end_line,
                    "score": score,
                }
                for file_path, block_type, name, start_line, end_line, score in results
            ]
        else:
            print("PyO3 bindings not available - search not supported")
            return []
    
    def index_incremental(self, root_path: Path) -> int:
        """Incremental indexing - only index changed files"""
        if HAS_PYO3 and self.indexer:
            return self.indexer.index_incremental(str(root_path))
        else:
            print("PyO3 bindings not available - incremental indexing not supported")
            return 0
    
    def validate_index(self) -> Dict[str, Any]:
        """Validate index integrity"""
        if HAS_PYO3 and self.indexer:
            result = self.indexer.validate_index()
            return {
                "total_files": result.get("total_files", 0),
                "total_blocks": result.get("total_blocks", 0),
                "orphaned_blocks": result.get("orphaned_blocks", 0),
                "missing_files": result.get("missing_files", []),
                "errors": result.get("errors", []),
            }
        else:
            print("PyO3 bindings not available - validation not supported")
            return {
                "total_files": 0,
                "total_blocks": 0,
                "orphaned_blocks": 0,
                "missing_files": [],
                "errors": [],
            }
    
    def repair_index(self) -> int:
        """Repair index (remove orphaned entries)"""
        if HAS_PYO3 and self.indexer:
            return self.indexer.repair_index()
        else:
            print("PyO3 bindings not available - repair not supported")
            return 0
    
    def watch_directory(self, path: Path) -> None:
        """Start watching a directory for changes"""
        # File watcher implementation would require additional setup
        # For now, this is a placeholder
        print(f"File watching not yet implemented - would watch {path}")
    
    def stop_watching(self) -> None:
        """Stop watching for changes"""
        print("File watching not yet implemented")
