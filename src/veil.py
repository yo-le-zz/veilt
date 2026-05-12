"""
Name : veil
Author : yo-le-zz
Version : 1.0.0
"""

# ClI app import
import typer
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# =========================================================
# INITIALISATION
# =========================================================
from commands import register_commands

app = typer.Typer()
register_commands(app)
console = Console()

# =========================================================
# Config and constants
# =========================================================

from config import VERSION, COMMANDS

# =========================================================
# OUTPUT ENGINE
# =========================================================
def output(data: dict, json_mode: bool):
    """
    Central output system:
    - JSON mode => raw JSON (machine readable)
    - Human mode => Rich table + colors
    """

    # =========================
    # MODE MACHINE (JSON)
    # =========================
    if json_mode:
        print(json.dumps(data, indent=2))
        return

    # =========================
    # MODE HUMAIN (RICH)
    # =========================

    table = Table(title="🛡  Veil - Commandes disponibles", header_style="bold cyan")

    table.add_column("Commande", style="bold magenta")
    table.add_column("Description", style="white")

    for cmd, desc in data.items():
        table.add_row(cmd, desc)

    console.print()
    console.print(Panel.fit(
        table,
        title="Veil CLI",
        subtitle=f"Version {VERSION}",
        border_style="green"
    ))

# =========================================================
# Commande d'aide
# =========================================================
@app.command()
def help(
    json_mode: bool = typer.Option(False, "--json", help="Raw JSON output")
):
    """Display available commands"""
    output(COMMANDS, json_mode)


@app.command()
def version(
    json_mode: bool = typer.Option(False, "--json", help="Raw JSON output")
):
    """Display version information"""

    data = {
        "name": "veil",
        "version": VERSION
    }

    output(data, json_mode)

# =========================================================
# ENTRYPOINT
# =========================================================
if __name__ == "__main__":
    app()