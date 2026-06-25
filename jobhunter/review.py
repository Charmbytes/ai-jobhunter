"""Interactive review: show ranked jobs, let you approve the ones to apply to."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import Job

console = Console()


def show_table(jobs: list[Job]) -> None:
    table = Table(title="Ranked matches", show_lines=False, expand=True)
    table.add_column("#", justify="right", style="bold")
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Level")
    table.add_column("Salary")
    table.add_column("Align", justify="right")
    table.add_column("Src")
    for i, j in enumerate(jobs, 1):
        align = f"{j.alignment:.0f}%"
        style = "green" if j.alignment >= 70 else ("yellow" if j.alignment >= 40 else "red")
        table.add_row(
            str(i), j.title, j.company, j.location or "-",
            j.experience_level or "-", j.salary_str(),
            f"[{style}]{align}[/{style}]", j.source,
        )
    console.print(table)


def _detail(job: Job, idx: int, total: int) -> None:
    matched = ", ".join(job.matched_skills) or "—"
    missing = ", ".join(job.missing_skills) or "—"
    desc = job.description.strip().replace("\n", " ")
    if len(desc) > 400:
        desc = desc[:400] + "…"
    body = (
        f"[bold cyan]{job.title}[/bold cyan]  —  {job.company}\n"
        f"[dim]{job.location} · {job.experience_level} · {job.salary_str()} · "
        f"{job.source}[/dim]\n\n"
        f"[green]You match:[/green] {matched}\n"
        f"[yellow]Missing:[/yellow]  {missing}\n"
        f"[bold]Alignment:[/bold] {job.alignment:.0f}%   "
        f"[bold]Score:[/bold] {job.score:.0f}\n\n"
        f"{desc}\n\n[blue underline]{job.url}[/blue underline]"
    )
    console.print(Panel(body, title=f"[{idx}/{total}]", border_style="cyan"))


def review(jobs: list[Job]) -> list[Job]:
    """Walk through jobs one by one. Returns the approved list."""
    if not jobs:
        console.print("[red]No jobs matched your filters.[/red]")
        return []

    show_table(jobs)
    console.print(
        "\n[bold]Review each job:[/bold] "
        "[green]y[/green]=approve  [red]n[/red]=skip  "
        "[cyan]o[/cyan]=open in browser  [yellow]a[/yellow]=approve all remaining  "
        "[magenta]q[/magenta]=stop reviewing\n"
    )

    approved: list[Job] = []
    i = 0
    total = len(jobs)
    while i < total:
        job = jobs[i]
        _detail(job, i + 1, total)
        choice = console.input("[bold]approve? (y/n/o/a/q): [/bold]").strip().lower()
        if choice == "o":
            import webbrowser
            webbrowser.open(job.url)
            continue  # re-prompt for the same job
        if choice == "y":
            approved.append(job)
        elif choice == "a":
            approved.extend(jobs[i:])
            break
        elif choice == "q":
            break
        i += 1

    console.print(f"\n[bold green]Approved {len(approved)} job(s) to apply to.[/bold green]")
    return approved
