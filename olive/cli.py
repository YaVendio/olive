"""Olive CLI using Typer with Rich output."""

import asyncio
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from olive.config import OliveConfig
from olive.temporal.worker import TemporalWorker

console = Console()
app = typer.Typer(
    name="olive",
    help="🫒 Olive - FastAPI + Temporal tool framework",
    rich_markup_mode="rich",
    add_completion=True,
)


def check_temporal_running(address: str = "localhost:7233") -> bool:
    """Check if Temporal server is running."""
    try:
        import httpx

        response = httpx.get(f"http://{address}/api/v1/system.info", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def start_temporal_dev_server() -> subprocess.Popen[bytes]:
    """Start Temporal dev server in background."""
    return subprocess.Popen(
        ["temporal", "server", "start-dev", "--db-filename", ".temporal.db"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@app.command()
def dev(
    host: Annotated[str, typer.Option("--host", "-h", help="Host to bind to")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind to")] = 8000,
    reload: Annotated[bool, typer.Option("--reload/--no-reload", help="Enable auto-reload")] = True,
    config_file: Annotated[Path | None, typer.Option("--config", "-c", help="Config file path")] = None,
):
    """
    🚀 Run Olive in development mode.

    This starts:
    - Local Temporal server (if needed)
    - Temporal worker
    - FastAPI server with hot-reload
    """
    console.print(Panel.fit("🫒 [bold green]Starting Olive Development Server[/bold green]", border_style="green"))

    # Load configuration
    config = OliveConfig.from_file(config_file) if config_file else OliveConfig()

    # Check and start Temporal if needed
    temporal_address = config.temporal.address

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Check Temporal
        task = progress.add_task("[cyan]Checking Temporal server...", total=None)

        temporal_process = None
        if not check_temporal_running(temporal_address):
            progress.update(task, description="[yellow]Starting local Temporal server...")
            temporal_process = start_temporal_dev_server()

            # Wait for Temporal to start
            for _ in range(30):  # 30 second timeout
                if check_temporal_running(temporal_address):
                    break
                asyncio.run(asyncio.sleep(1))
            else:
                console.print("[red]❌ Failed to start Temporal server![/red]")
                raise typer.Exit(1)

        progress.update(task, description="[green]✓ Temporal server ready!")
        progress.remove_task(task)

    # Display startup info
    table = Table(title="🫒 Olive Configuration", show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("FastAPI", f"http://{host}:{port}")
    table.add_row("Temporal", f"{temporal_address}")
    table.add_row("Hot Reload", "✓ Enabled" if reload else "✗ Disabled")
    table.add_row("Docs", f"http://{host}:{port}/docs")

    console.print(table)
    console.print()

    worker: TemporalWorker | None = None
    try:
        # Start worker in background thread
        console.print("[cyan]Starting Temporal worker...[/cyan]")
        worker = TemporalWorker(config)
        worker.start_background()

        # Start FastAPI
        console.print("[cyan]Starting FastAPI server...[/cyan]")
        console.print()

        import uvicorn

        uvicorn.run(
            "main:app" if Path("main.py").exists() else "olive.server.app:create_app",
            host=host,
            port=port,
            reload=reload,
            factory=not Path("main.py").exists(),
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Shutting down Olive...[/yellow]")
    finally:
        # Stop worker
        if worker is not None:
            worker.stop()

        # Stop Temporal server if we started it
        if temporal_process:
            console.print("[dim]Stopping Temporal server...[/dim]")
            temporal_process.terminate()
            temporal_process.wait()


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", "-h", help="Host to bind to")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind to")] = 8000,
    temporal_address: Annotated[str | None, typer.Option("--temporal-address", help="Temporal server address")] = None,
    temporal_namespace: Annotated[str | None, typer.Option("--temporal-namespace", help="Temporal namespace")] = None,
    config_file: Annotated[Path | None, typer.Option("--config", "-c", help="Config file path")] = None,
):
    """
    🏭 Run Olive in production mode.

    Connect to an existing Temporal server (local or cloud).
    """
    console.print(Panel.fit("🫒 [bold blue]Starting Olive Production Server[/bold blue]", border_style="blue"))

    # Load configuration
    config = OliveConfig.from_file(config_file) if config_file else OliveConfig()

    # Override with CLI options
    if temporal_address:
        config.temporal.address = temporal_address
    if temporal_namespace:
        config.temporal.namespace = temporal_namespace

    # Display configuration
    table = Table(title="🫒 Production Configuration", show_header=False, box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="blue")

    table.add_row("FastAPI", f"http://{host}:{port}")
    table.add_row("Temporal", config.temporal.address)
    table.add_row("Namespace", config.temporal.namespace)

    console.print(table)
    console.print()

    worker: TemporalWorker | None = None
    try:
        # Start worker
        console.print("[cyan]Starting Temporal worker...[/cyan]")
        worker = TemporalWorker(config)
        worker.start_background()

        # Start FastAPI
        console.print("[cyan]Starting FastAPI server...[/cyan]")
        console.print()

        import uvicorn

        uvicorn.run(
            "main:app" if Path("main.py").exists() else "olive.server.app:create_app",
            host=host,
            port=port,
            factory=not Path("main.py").exists(),
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Shutting down Olive...[/yellow]")
    finally:
        # Stop worker
        if worker is not None:
            worker.stop()


@app.command()
def init(
    path: Annotated[Path | None, typer.Argument(help="Project directory")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing files")] = False,
):
    """
    🌱 Initialize a new Olive project.

    Creates a starter project with example tools.
    """
    if path is None:
        path = Path.cwd()

    console.print(Panel.fit("🫒 [bold green]Initializing Olive Project[/bold green]", border_style="green"))

    # Create example main.py
    main_content = '''"""Example Olive project."""

from olive import olive_tool, create_app

app = create_app()  # FastAPI app with Olive routes


@olive_tool(description="Translate text to another language")
async def translate(text: str, target_language: str = "es") -> dict:
    """Translate text to the target language."""
    # In a real app, you'd use a translation service
    translations = {
        "es": "Hola",
        "fr": "Bonjour",
        "de": "Hallo",
    }
    greeting = translations.get(target_language, "Hello")
    return {
        "original": text,
        "translated": f"{greeting}! (Translated: {text})",
        "language": target_language,
    }


@olive_tool(
    description="Analyze sentiment of text",
    timeout_seconds=30,
    retry_policy={"max_attempts": 3},
)
async def analyze_sentiment(text: str) -> dict:
    """Analyze the sentiment of the provided text."""
    # Simulate some processing
    import asyncio
    await asyncio.sleep(1)

    # In a real app, you'd use an NLP service
    positive_words = ["good", "great", "excellent", "happy", "love"]
    negative_words = ["bad", "terrible", "hate", "sad", "awful"]

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        sentiment = "positive"
        score = 0.8
    elif negative_count > positive_count:
        sentiment = "negative"
        score = 0.2
    else:
        sentiment = "neutral"
        score = 0.5

    return {
        "text": text,
        "sentiment": sentiment,
        "score": score,
        "confidence": 0.9,
    }


if __name__ == "__main__":
    # Run with: olive dev
    import olive
    olive.run_dev()
'''

    # Create .olive.yaml
    config_content = """# Olive Configuration
temporal:
  address: localhost:7233
  namespace: default
  task_queue: olive-tools

server:
  host: 0.0.0.0
  port: 8000

tools:
  default_timeout: 300
  default_retry_attempts: 3
"""

    # Create files
    main_path = path / "main.py"
    config_path = path / ".olive.yaml"

    files_created = []

    if not main_path.exists() or force:
        main_path.write_text(main_content)
        files_created.append("main.py")

    if not config_path.exists() or force:
        config_path.write_text(config_content)
        files_created.append(".olive.yaml")

    if files_created:
        console.print(f"[green]✓ Created files:[/green] {', '.join(files_created)}")
    else:
        console.print("[yellow]⚠ Files already exist. Use --force to overwrite.[/yellow]")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Run [cyan]olive dev[/cyan] to start the development server")
    console.print("2. Visit [cyan]http://localhost:8000/docs[/cyan] to see your tools")
    console.print("3. Add more tools with [cyan]@olive_tool[/cyan] decorator")


@app.command()
def version():
    """Show Olive version."""
    from olive import __version__

    console.print(f"[green]🫒 Olive v{__version__}[/green]")


def main():
    """Main CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
