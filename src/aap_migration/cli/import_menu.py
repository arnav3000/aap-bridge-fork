"""Enhanced import menu with dependency validation and error handling."""

import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from aap_migration.cli.utils import echo_error, echo_info, echo_success, echo_warning


def run_command(args: list[str], ctx: Any = None) -> int:
    """Run a CLI command and return exit code."""
    import subprocess

    cmd = [sys.argv[0]]

    if ctx and ctx.obj and ctx.obj.config_path:
        cmd.extend(["--config", str(ctx.obj.config_path)])

    cmd.extend(args)

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        echo_error(f"Error running command: {e}")
        return 1


def show_import_status(ctx: Any) -> None:
    """Display current import status and progress."""
    console = Console()

    try:
        from aap_migration.migration.state import MigrationState

        state = MigrationState()

        # Get all resource types with progress
        all_stats = []
        resource_types = [
            "organizations", "users", "teams", "credential_types",
            "credentials", "execution_environments", "projects",
            "inventories", "hosts", "job_templates",
            "workflow_job_templates", "schedules"
        ]

        for rtype in resource_types:
            stats = state.get_import_stats(rtype)
            if stats["total_exported"] > 0:
                all_stats.append({
                    "type": rtype,
                    "total": stats["total_exported"],
                    "completed": stats["completed"],
                    "failed": stats["failed"],
                    "pending": stats["pending"],
                    "percent": stats["percent_complete"]
                })

        if not all_stats:
            console.print("\n[yellow]No import progress found. Run export first.[/yellow]\n")
            return

        # Create status table
        table = Table(title="Import Status", show_header=True, header_style="bold cyan")
        table.add_column("Resource Type", style="cyan", width=25)
        table.add_column("Total", justify="right", width=8)
        table.add_column("Completed", justify="right", width=10, style="green")
        table.add_column("Failed", justify="right", width=8, style="red")
        table.add_column("Pending", justify="right", width=8, style="yellow")
        table.add_column("Progress", width=20)

        for stat in all_stats:
            # Progress bar
            percent = stat["percent"]
            bar_length = 15
            filled = int(bar_length * percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)

            # Color code based on status
            if stat["failed"] > 0:
                status_color = "red"
            elif stat["pending"] > 0:
                status_color = "yellow"
            else:
                status_color = "green"

            table.add_row(
                stat["type"],
                str(stat["total"]),
                str(stat["completed"]),
                str(stat["failed"]) if stat["failed"] > 0 else "-",
                str(stat["pending"]) if stat["pending"] > 0 else "-",
                f"[{status_color}]{bar}[/{status_color}] {percent:.1f}%"
            )

        console.print("\n")
        console.print(table)
        console.print("\n")

        # Summary
        totals = {
            "total": sum(s["total"] for s in all_stats),
            "completed": sum(s["completed"] for s in all_stats),
            "failed": sum(s["failed"] for s in all_stats),
            "pending": sum(s["pending"] for s in all_stats),
        }

        console.print(f"[bold]Overall Progress:[/bold]")
        console.print(f"  Total Resources: {totals['total']}")
        console.print(f"  [green]✓ Completed: {totals['completed']}[/green]")
        if totals['failed'] > 0:
            console.print(f"  [red]✗ Failed: {totals['failed']}[/red]")
        if totals['pending'] > 0:
            console.print(f"  [yellow]⧗ Pending: {totals['pending']}[/yellow]")
        console.print()

    except Exception as e:
        echo_error(f"Failed to get import status: {e}")


def show_failed_resources(ctx: Any) -> None:
    """Display failed resources with error details."""
    console = Console()

    try:
        from aap_migration.migration.state import MigrationState

        state = MigrationState()

        # Query failed resources
        query = """
        SELECT
            resource_type,
            source_id,
            source_name,
            error_message,
            updated_at
        FROM migration_progress
        WHERE status = 'failed'
        ORDER BY resource_type, source_id
        """

        cursor = state.conn.execute(query)
        failed = cursor.fetchall()

        if not failed:
            console.print("\n[green]✓ No failed resources![/green]\n")
            return

        # Create failed resources table
        table = Table(title="Failed Resources", show_header=True, header_style="bold red")
        table.add_column("Type", style="cyan", width=20)
        table.add_column("Source ID", justify="right", width=10)
        table.add_column("Name", width=25)
        table.add_column("Error", width=50)

        for row in failed:
            error = row[3] if row[3] else "Unknown error"
            # Truncate long errors
            if len(error) > 47:
                error = error[:44] + "..."

            table.add_row(
                row[0],  # resource_type
                str(row[1]),  # source_id
                row[2] if row[2] else "N/A",  # source_name
                error
            )

        console.print("\n")
        console.print(table)
        console.print(f"\n[bold red]Total Failed: {len(failed)}[/bold red]\n")

    except Exception as e:
        echo_error(f"Failed to get error details: {e}")


def import_submenu(ctx: Any) -> None:
    """Enhanced import submenu with validation and retry options."""
    console = Console()

    while True:
        console.clear()
        console.print(
            Panel.fit(
                "[bold cyan]Import Resources[/bold cyan]\n\n"
                "1. Pre-flight Check (Validate Dependencies)\n"
                "2. Import All Resources\n"
                "3. Import Phase 1 (Base Resources)\n"
                "4. Import Phase 2 (Projects + Automation)\n"
                "5. Retry Failed Resources\n"
                "6. View Import Status\n"
                "7. View Failed Resources\n"
                "b. Back to Main Menu",
                title="Import Menu",
                border_style="cyan",
            )
        )

        choice = Prompt.ask(
            "Select an option",
            choices=["1", "2", "3", "4", "5", "6", "7", "b"],
            default="b"
        )

        if choice.lower() == "b":
            break

        console.print()

        if choice == "1":
            # Pre-flight dependency check
            echo_info("Running pre-flight dependency validation...")
            run_command(["import", "--check-dependencies"])

        elif choice == "2":
            # Import all resources
            console.print("[yellow]This will import all resources in the correct order.[/yellow]")
            confirm = Prompt.ask("Continue?", choices=["y", "n"], default="n")
            if confirm == "y":
                run_command(["import"])

        elif choice == "3":
            # Phase 1
            console.print("[yellow]Phase 1: Organizations, Users, Teams, Credentials, Projects, Inventories[/yellow]")
            confirm = Prompt.ask("Continue?", choices=["y", "n"], default="n")
            if confirm == "y":
                run_command(["import", "--phase", "phase1"])

        elif choice == "4":
            # Phase 2
            console.print("[yellow]Phase 2: Job Templates, Workflows, Schedules[/yellow]")
            confirm = Prompt.ask("Continue?", choices=["y", "n"], default="n")
            if confirm == "y":
                run_command(["import", "--phase", "phase2"])

        elif choice == "5":
            # Retry failed
            console.print("[yellow]This will retry all previously failed resources.[/yellow]")
            confirm = Prompt.ask("Continue?", choices=["y", "n"], default="n")
            if confirm == "y":
                run_command(["retry", "failed", "-y"])

        elif choice == "6":
            # View status
            show_import_status(ctx)

        elif choice == "7":
            # View failed resources
            show_failed_resources(ctx)

        if choice != "6" and choice != "7":
            Prompt.ask("\nPress Enter to continue...")
