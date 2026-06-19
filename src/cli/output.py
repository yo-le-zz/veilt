"""
veilt.cli.output
=================
Small Rich-based output helpers shared by every CLI command.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def success(message: str) -> None:
    console.print(f"[bold green]\u2713[/bold green] {message}")


def error(message: str) -> None:
    err_console.print(f"[bold red]\u2717[/bold red] {message}")


def warning(message: str) -> None:
    console.print(f"[bold yellow]![/bold yellow] {message}")


def info(message: str) -> None:
    console.print(f"[bold cyan]i[/bold cyan] {message}")


def print_status(data: Dict[str, Any], title: Optional[str] = None) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(str(key), str(value))
    console.print(table)


def print_entries(entries: list) -> None:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Accesses")
    table.add_column("TTL")
    for e in entries:
        table.add_row(
            str(e.get("id", "")),
            str(e.get("status", "")),
            str(e.get("created_at", "")),
            str(e.get("access_count", 0)),
            str(e.get("ttl") or "-"),
        )
    console.print(table)
