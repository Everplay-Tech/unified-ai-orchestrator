"""Indexing CLI commands"""

import typer
import signal
import sys
import threading
from pathlib import Path
from typing import Optional
from .manager import IndexerManager

app = typer.Typer()


@app.command()
def index(
    project_id: str = typer.Argument(..., help="Project ID"),
    path: str = typer.Argument(..., help="Path to index"),
    db_path: str = typer.Option("data/index.db", help="Database path"),
):
    """Index a directory or file"""
    manager = IndexerManager(project_id, Path(db_path))
    indexed = manager.index_directory(Path(path))
    typer.echo(f"Indexed {indexed} files")


@app.command()
def search(
    project_id: str = typer.Argument(..., help="Project ID"),
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, help="Result limit"),
    db_path: str = typer.Option("data/index.db", help="Database path"),
):
    """Search indexed codebase"""
    manager = IndexerManager(project_id, Path(db_path))
    results = manager.search(query, limit)
    
    for result in results:
        typer.echo(f"{result.get('file_path')}:{result.get('start_line')} - {result.get('name', 'unknown')}")


@app.command()
def watch(
    project_id: str = typer.Argument(..., help="Project ID"),
    path: str = typer.Argument(..., help="Path to watch"),
    db_path: str = typer.Option("data/index.db", help="Database path"),
):
    """Watch directory for changes and auto-index"""
    manager = IndexerManager(project_id, Path(db_path))
    
    # Thread-safe shutdown flag (signal handlers should only set flags)
    shutdown_event = threading.Event()
    
    # Setup signal handlers for graceful shutdown
    # Signal handlers should only set flags, not call complex operations
    def signal_handler(signum, frame):
        """Signal handler - only sets a flag, no complex operations"""
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Error callback for file processing errors
    def error_callback(error_msg: str):
        typer.echo(f"Error processing file change: {error_msg}", err=True)
    
    typer.echo(f"Watching {path} for changes... (Press Ctrl+C to stop)")
    
    try:
        manager.watch_directory(Path(path), error_callback=error_callback)
        
        # Keep the process alive, checking shutdown flag periodically
        # This allows cleanup to happen in the main thread, not in signal handler
        try:
            while not shutdown_event.is_set():
                # Wait with timeout to periodically check shutdown flag
                shutdown_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            shutdown_event.set()
        
        # Cleanup happens here in main thread (safe)
        if shutdown_event.is_set():
            typer.echo("\nShutting down file watcher...")
            
    except RuntimeError as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        # Cleanup in main thread - safe to call complex operations here
        manager.stop_watching()


@app.command()
def incremental(
    project_id: str = typer.Argument(..., help="Project ID"),
    path: str = typer.Argument(..., help="Path to index"),
    db_path: str = typer.Option("data/index.db", help="Database path"),
):
    """Incremental indexing - only index changed files"""
    manager = IndexerManager(project_id, Path(db_path))
    indexed = manager.index_incremental(Path(path))
    typer.echo(f"Indexed {indexed} changed files")


@app.command()
def validate(
    project_id: str = typer.Argument(..., help="Project ID"),
    db_path: str = typer.Option("data/index.db", help="Database path"),
):
    """Validate index integrity"""
    manager = IndexerManager(project_id, Path(db_path))
    result = manager.validate_index()
    typer.echo(f"Validation complete:")
    typer.echo(f"  Total files: {result.get('total_files', 0)}")
    typer.echo(f"  Total blocks: {result.get('total_blocks', 0)}")
    typer.echo(f"  Orphaned blocks: {result.get('orphaned_blocks', 0)}")
    if result.get('errors'):
        typer.echo(f"  Errors: {len(result['errors'])}")


@app.command()
def repair(
    project_id: str = typer.Argument(..., help="Project ID"),
    db_path: str = typer.Option("data/index.db", help="Database path"),
):
    """Repair index (remove orphaned entries)"""
    manager = IndexerManager(project_id, Path(db_path))
    repaired = manager.repair_index()
    typer.echo(f"Repaired {repaired} issues")


if __name__ == "__main__":
    app()
