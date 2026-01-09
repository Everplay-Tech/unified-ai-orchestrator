"""Indexing CLI commands"""

import typer
from pathlib import Path
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
    typer.echo(f"Watching {path} for changes...")
    manager.watch_directory(Path(path))


if __name__ == "__main__":
    app()
