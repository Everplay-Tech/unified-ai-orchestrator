"""CLI entry point"""

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

import secrets
from ..adapters import ClaudeAdapter, GPTAdapter, ToolAdapter
from ..config import load_config, save_config, Config, ToolConfig
from ..utils.auth import get_api_key, set_api_key, get_secret
from ..utils.auth import set_secret as set_secret_auth
from ..router import Router
from ..context_manager import ContextManager
from ..migrations.cli import run_migrations, migration_status, rollback_migration

app = typer.Typer(help="Unified AI Orchestration System")
console = Console()


def get_adapters(config: Config) -> dict:
    """Get configured adapters"""
    adapters = {}
    
    # Claude adapter
    if "claude" in config.tools:
        tool_config = config.tools["claude"]
        if tool_config.enabled:
            api_key = tool_config.api_key or get_api_key("anthropic")
            if api_key:
                adapters["claude"] = ClaudeAdapter(
                    api_key=api_key,
                    model=tool_config.model or "claude-3-5-sonnet-20241022",
                )
    
    # GPT adapter
    if "gpt" in config.tools:
        tool_config = config.tools["gpt"]
        if tool_config.enabled:
            api_key = tool_config.api_key or get_api_key("openai")
            if api_key:
                adapters["gpt"] = GPTAdapter(
                    api_key=api_key,
                    model=tool_config.model or "gpt-4",
                )
    
    return adapters


@app.command()
def chat(
    message: str = typer.Argument(..., help="Your message/question"),
    tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Explicit tool to use"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project path"),
):
    """Chat with the unified AI interface"""
    asyncio.run(_chat_async(message, tool, project))


async def _chat_async(message: str, tool: Optional[str], project: Optional[str]):
    """Async chat implementation"""
    config = load_config()
    adapters = get_adapters(config)
    
    if not adapters:
        console.print("[red]No AI tools configured. Run 'uai config' to set up.[/red]")
        raise typer.Exit(1)
    
    # Initialize router
    routing_rules = {
        "code_editing": config.routing.code_editing,
        "research": config.routing.research,
        "general_chat": config.routing.general_chat,
    }
    router = Router(routing_rules, config.routing.default_tool)
    
    # Initialize context manager
    context_mgr = ContextManager(config=config)
    await context_mgr.initialize()
    
    # Get or create conversation context
    conversation_id = None  # Could be passed as parameter in future
    context = await context_mgr.get_or_create_context(
        conversation_id=conversation_id,
        project_id=project,
    )
    
    # Route request
    routing_decision = router.route(
        message=message,
        conversation_id=context.conversation_id,
        project_id=project,
        explicit_tool=tool,
    )
    
    # Select tool
    selected_tool_name = None
    if tool:
        selected_tool_name = tool
    else:
        # Use first available tool from routing decision
        for tool_name in routing_decision["selected_tools"]:
            if tool_name in adapters:
                selected_tool_name = tool_name
                break
    
    if not selected_tool_name or selected_tool_name not in adapters:
        console.print(f"[red]No suitable tool available. Available: {list(adapters.keys())}[/red]")
        raise typer.Exit(1)
    
    selected_tool = adapters[selected_tool_name]
    
    console.print(f"[dim]Using tool: {selected_tool.name} ({routing_decision['reasoning']})[/dim]\n")
    
    # Prepare messages with history
    from ..adapters.base import Message as AdapterMessage, Context as AdapterContext
    messages = []
    
    # Add conversation history
    for msg in context.messages[-10:]:  # Last 10 messages for context
        messages.append(AdapterMessage(role=msg.role, content=msg.content))
    
    # Add current message
    messages.append(AdapterMessage(role="user", content=message))
    
    # Prepare adapter context
    adapter_context = None
    if project or context.codebase_context:
        adapter_context = AdapterContext(
            conversation_id=context.conversation_id,
            project_id=project or context.project_id,
            codebase_context=context.codebase_context,
        )
    
    # Make request
    try:
        response = await selected_tool.chat(messages, adapter_context)
        
        # Save to context
        await context_mgr.add_message(context, "user", message)
        await context_mgr.add_message(context, "assistant", response.content)
        await context_mgr.add_tool_call(
            context,
            selected_tool.name,
            message,
            response.content,
        )
        
        console.print(response.content)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def tools():
    """List available AI tools"""
    config = load_config()
    adapters = get_adapters(config)
    
    if not adapters:
        console.print("[yellow]No tools configured.[/yellow]")
        return
    
    console.print("[bold]Available Tools:[/bold]\n")
    for name, adapter in adapters.items():
        caps = adapter.capabilities
        console.print(f"  [cyan]{name}[/cyan]")
        console.print(f"    Model: {adapter.model if hasattr(adapter, 'model') else 'N/A'}")
        console.print(f"    Streaming: {'Yes' if caps.supports_streaming else 'No'}")
        console.print(f"    Code Context: {'Yes' if caps.supports_code_context else 'No'}")
        console.print()


@app.command()
def config():
    """Configure API keys and settings"""
    console.print("[bold]Unified AI Configuration[/bold]\n")
    
    config = load_config()
    
    # Configure Claude
    console.print("[cyan]Claude (Anthropic)[/cyan]")
    if "claude" not in config.tools:
        config.tools["claude"] = ToolConfig()
    
    claude_config = config.tools["claude"]
    
    # Check if API key exists
    api_key = get_api_key("anthropic")
    if not api_key:
        api_key = Prompt.ask("Enter Anthropic API key", password=True)
        if api_key:
            set_api_key("anthropic", api_key)
            console.print("[green]API key saved[/green]")
    else:
        console.print("[green]API key already configured[/green]")
        if Prompt.ask("Update API key?", choices=["y", "n"], default="n") == "y":
            api_key = Prompt.ask("Enter new Anthropic API key", password=True)
            if api_key:
                set_api_key("anthropic", api_key)
                console.print("[green]API key updated[/green]")
    
    claude_config.enabled = True
    claude_config.api_key_env = "ANTHROPIC_API_KEY"
    if not claude_config.model:
        claude_config.model = "claude-3-5-sonnet-20241022"
    
    console.print()
    
    # Configure GPT
    console.print("[cyan]GPT (OpenAI)[/cyan]")
    if "gpt" not in config.tools:
        config.tools["gpt"] = ToolConfig()
    
    gpt_config = config.tools["gpt"]
    
    api_key = get_api_key("openai")
    if not api_key:
        api_key = Prompt.ask("Enter OpenAI API key (or press Enter to skip)", password=True)
        if api_key:
            set_api_key("openai", api_key)
            console.print("[green]API key saved[/green]")
            gpt_config.enabled = True
    else:
        console.print("[green]API key already configured[/green]")
        if Prompt.ask("Update API key?", choices=["y", "n"], default="n") == "y":
            api_key = Prompt.ask("Enter new OpenAI API key", password=True)
            if api_key:
                set_api_key("openai", api_key)
                console.print("[green]API key updated[/green]")
        gpt_config.enabled = True
    
    gpt_config.api_key_env = "OPENAI_API_KEY"
    if not gpt_config.model:
        gpt_config.model = "gpt-4"
    
    # Save config
    save_config(config)
    console.print("\n[green]Configuration saved![/green]")


@app.command()
def mobile_key(
    generate: bool = typer.Option(False, "--generate", "-g", help="Generate a new API key"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current API key"),
):
    """Manage mobile API key for remote access"""
    if generate:
        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)
        
        # Store in keyring
        try:
            set_secret_auth("mobile_api_key", api_key)
            console.print("\n[green]✓ Mobile API key generated and saved![/green]")
            console.print(f"\n[bold]Your API key:[/bold]")
            console.print(f"[cyan]{api_key}[/cyan]\n")
            console.print("[yellow]⚠️  Save this key securely. You'll need it to access the mobile interface.[/yellow]")
            console.print("\nSet it as an environment variable:")
            console.print(f"[dim]export MOBILE_API_KEY={api_key}[/dim]\n")
        except Exception as e:
            console.print(f"[red]Failed to save API key: {e}[/red]")
            raise typer.Exit(1)
    elif show:
        # Show current API key
        api_key = get_secret("mobile_api_key")
        if api_key:
            console.print("\n[bold]Current mobile API key:[/bold]")
            console.print(f"[cyan]{api_key}[/cyan]\n")
        else:
            console.print("\n[yellow]No mobile API key found.[/yellow]")
            console.print("Generate one with: [cyan]uai mobile-key --generate[/cyan]\n")
    else:
        # Show current key or prompt to generate
        api_key = get_secret("mobile_api_key")
        if api_key:
            console.print("\n[bold]Current mobile API key:[/bold]")
            console.print(f"[cyan]{api_key}[/cyan]\n")
            console.print("Generate a new key with: [cyan]uai mobile-key --generate[/cyan]\n")
        else:
            console.print("\n[yellow]No mobile API key configured.[/yellow]")
            console.print("Generate one with: [cyan]uai mobile-key --generate[/cyan]\n")


@app.command()
def migrations(
    command: str = typer.Argument(..., help="Command: status, up, or down"),
    db_path: Optional[str] = typer.Option(None, "--db-path", help="Path to database file (defaults to config)"),
    target_version: Optional[int] = typer.Option(None, "--version", "-v", help="Target version for up/down"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run mode (status only)"),
):
    """Manage database migrations"""
    # Get database path from config if not provided
    if db_path is None:
        config = load_config()
        db_path = config.storage.db_path
    
    db_path_obj = Path(db_path).expanduser()
    
    if command == "status":
        migration_status(db_path_obj)
    elif command == "up":
        run_migrations(db_path_obj, target_version=target_version, dry_run=dry_run)
    elif command == "down":
        if target_version is None:
            console.print("[red]Target version required for rollback. Use --version[/red]")
            raise typer.Exit(1)
        rollback_migration(db_path_obj, target_version)
    else:
        console.print(f"[red]Unknown command: {command}. Use: status, up, or down[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
