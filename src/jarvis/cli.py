"""Kommandozeile fuer Jarvis.

Befehle:
    jarvis doctor            - prueft Einrichtung (ohne API-Aufruf, kostenlos)
    jarvis workspace         - zeigt den Workspace und seine Dateien
    jarvis ask "..."         - eine Aufgabe, eine Antwort
    jarvis chat              - Gespraech mit Gedaechtnis (bis "exit")
    jarvis serve             - startet nur den lokalen Server
    jarvis dev               - startet Server UND Oberflaeche (der normale Weg)
"""

from __future__ import annotations

import contextlib
import signal
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config import PROJECT_ROOT, Settings, load_settings
from .core.agent import Agent, AgentEvent
from .core.models.anthropic_model import AnthropicModel
from .core.tools.files import default_tools
from .core.tools.registry import ToolRegistry
from .errors import JarvisError
from .workspace import Workspace

app = typer.Typer(
    add_completion=False,
    help="Jarvis - dein lokaler Agent. Arbeitet nur im Workspace-Ordner.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

_EVENT_STYLE = {
    "thinking": ("[dim]…[/dim]", "dim"),
    "tool": ("[cyan]▸[/cyan]", "cyan"),
    "blocked": ("[yellow]⛔[/yellow]", "yellow"),
    "error": ("[red]✗[/red]", "red"),
}


def _show_event(event: AgentEvent) -> None:
    symbol, style = _EVENT_STYLE.get(event.kind, ("·", "white"))
    text = event.message if len(event.message) < 400 else event.message[:400] + " …"
    console.print(f"  {symbol} [{style}]{text}[/{style}]")


def _build_agent(settings: Settings, verbose: bool) -> tuple[Agent, Workspace]:
    workspace = Workspace.open(settings.workspace_path)
    tools = ToolRegistry(default_tools(workspace, settings.max_read_bytes))
    model = AnthropicModel(
        api_key=settings.require_api_key(),
        model_id=settings.model,
        max_tokens=settings.max_tokens,
    )
    agent = Agent(
        model=model,
        tools=tools,
        max_steps=settings.max_steps,
        on_event=_show_event if verbose else None,
    )
    return agent, workspace


def _fail(message: str) -> None:
    err_console.print(f"[red]Fehler:[/red] {message}")
    raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Zeigt die Version."""
    console.print(f"Jarvis {__version__} (Python {sys.version.split()[0]})")


@app.command()
def doctor() -> None:
    """Prueft die Einrichtung. Kostet nichts, ruft die API nicht auf."""
    console.print("[bold]Jarvis-Selbsttest[/bold]\n")
    settings = load_settings()

    env_file = PROJECT_ROOT / ".env"
    env_zustand = (
        "[green]gefunden[/green]"
        if env_file.exists()
        else "[red]fehlt[/red] (kopiere .env.example nach .env)"
    )
    console.print(f"  .env-Datei      : {env_zustand}")

    key = settings.anthropic_api_key
    if key and key.get_secret_value().strip():
        secret = key.get_secret_value()
        console.print(f"  API-Key         : [green]gesetzt[/green] ({secret[:7]}…{secret[-4:]})")
    else:
        console.print("  API-Key         : [red]fehlt[/red] (ANTHROPIC_API_KEY in der .env)")

    try:
        workspace = Workspace.open(settings.workspace_path)
        count = len(workspace.iter_files())
        console.print(f"  Workspace       : [green]{workspace.root}[/green] ({count} Datei(en))")
    except JarvisError as exc:
        console.print(f"  Workspace       : [red]{exc}[/red]")

    console.print(f"  Modell          : {settings.model}")
    console.print(f"  Schrittlimit    : {settings.max_steps}")
    console.print(f"  max_tokens      : {settings.max_tokens}")

    tools = ToolRegistry(default_tools(Workspace.open(settings.workspace_path)))
    names = ", ".join(f"{t.name} ({t.risk.label})" for t in tools)
    console.print(f"  Werkzeuge       : {names}")
    console.print("\n[dim]Nur-Lese-Betrieb: Schreiben und Ausfuehren kommen in Etappe 4.[/dim]")


@app.command()
def workspace() -> None:
    """Zeigt den Workspace-Ordner und was darin liegt."""
    settings = load_settings()
    space = Workspace.open(settings.workspace_path)
    console.print(f"[bold]Workspace:[/bold] {space.root}\n")
    files = space.iter_files()
    if not files:
        console.print("[dim]Noch leer. Lege Dateien hier ab, damit Jarvis sie lesen kann.[/dim]")
        return
    for path in files:
        console.print(f"  {space.label(path)}  [dim]({path.stat().st_size} Bytes)[/dim]")
    console.print(f"\n[dim]{len(files)} Datei(en)[/dim]")


@app.command()
def ask(
    task: Annotated[str, typer.Argument(help="Was soll Jarvis tun?")],
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Zwischenschritte ausblenden.")
    ] = False,
) -> None:
    """Stellt Jarvis eine Aufgabe und zeigt die Antwort."""
    settings = load_settings()
    try:
        agent, space = _build_agent(settings, verbose=not quiet)
    except JarvisError as exc:
        _fail(str(exc))
        return

    if not quiet:
        console.print(f"[dim]Workspace: {space.root} · Modell: {settings.model}[/dim]\n")
    try:
        result = agent.run(task)
    except JarvisError as exc:
        _fail(str(exc))
        return

    console.print(Panel(result.answer, title="Jarvis", border_style="green"))
    console.print(
        f"[dim]{result.steps} Schritt(e), {result.tool_calls} Werkzeugaufruf(e), "
        f"{result.usage.input_tokens} Tokens rein / {result.usage.output_tokens} raus[/dim]"
    )


@app.command()
def chat(
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Zwischenschritte ausblenden.")
    ] = False,
) -> None:
    """Gespraech mit Gedaechtnis. Beenden mit 'exit' oder Strg+C."""
    settings = load_settings()
    try:
        agent, space = _build_agent(settings, verbose=not quiet)
    except JarvisError as exc:
        _fail(str(exc))
        return

    console.print(f"[bold]Jarvis[/bold] · Workspace: {space.root} · Modell: {settings.model}")
    console.print("[dim]'exit' beendet, 'reset' vergisst das Gespraech.[/dim]\n")

    total = agent  # nur zur Lesbarkeit
    while True:
        try:
            task = console.input("[bold cyan]du >[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Tschuess.[/dim]")
            return
        if task.lower() in {"exit", "quit", ":q"}:
            console.print("[dim]Tschuess.[/dim]")
            return
        if task.lower() == "reset":
            total.reset()
            console.print("[dim]Gespraech vergessen.[/dim]\n")
            continue
        if not task:
            continue
        try:
            result = total.run(task)
        except JarvisError as exc:
            err_console.print(f"[red]Fehler:[/red] {exc}\n")
            continue
        console.print(Panel(result.answer, title="Jarvis", border_style="green"))
        verbrauch = result.usage
        console.print(
            f"[dim]{verbrauch.input_tokens} Tokens rein / {verbrauch.output_tokens} raus[/dim]\n"
        )


# ---------------------------------------------------------------------------
# Oberflaeche (Etappe 1)
# ---------------------------------------------------------------------------


@app.command()
def serve() -> None:
    """Startet nur den lokalen Server (ohne Oberflaeche).

    Nuetzlich zum Testen der Endpunkte. Fuer den normalen Betrieb ist
    `jarvis dev` gedacht.
    """
    from .server.security import create_session_token
    from .server.start import pruefadresse, pruefe_port_frei
    from .server.start import serve as _serve

    settings = load_settings()

    # Erst pruefen, dann melden: sonst steht "Server laeuft" auf dem
    # Bildschirm, obwohl der Start gleich scheitert.
    try:
        pruefe_port_frei(settings.host, settings.port)
    except JarvisError as fehler:
        err_console.print(Panel(str(fehler), title="Start nicht moeglich", border_style="red"))
        raise typer.Exit(code=1) from None

    token = create_session_token(settings)
    console.print(
        Panel(
            f"Server laeuft auf [bold]http://{settings.host}:{settings.port}[/bold]\n"
            f"Sitzungs-Token: [dim]{token}[/dim]\n\n"
            f"Test im Browser:\n  {pruefadresse(settings, token)}\n\n"
            "[yellow]Ohne dieses Token antwortet der Server nicht.[/yellow]\n"
            "Beenden mit Strg+C.",
            title="Jarvis Server",
            border_style="cyan",
        )
    )
    _serve(settings, token)


@app.command()
def dev() -> None:
    """Startet Server und Oberflaeche zusammen - so benutzt du Jarvis.

    Zwei Prozesse: der Python-Server (Port 8765) und der Vite-Server, der
    die Oberflaeche ausliefert (Port 5173). Strg+C beendet beide.
    """
    from .server.security import create_session_token
    from .server.start import (
        beende_vite,
        frontend_ordner,
        npm_befehl,
        pruefe_port_frei,
        startadresse,
        starte_vite,
    )
    from .server.start import serve as _serve

    settings = load_settings()

    # Beide Ports pruefen, bevor irgendetwas startet - sonst bleibt bei
    # einem Fehlschlag ein halb gestarteter Vite-Prozess zurueck.
    for port, wofuer in ((settings.port, "Server"), (settings.ui_dev_port, "Oberflaeche")):
        try:
            pruefe_port_frei(settings.host, port)
        except JarvisError as fehler:
            err_console.print(
                Panel(f"{wofuer}: {fehler}", title="Start nicht moeglich", border_style="red")
            )
            raise typer.Exit(code=1) from None

    if not (frontend_ordner() / "node_modules").is_dir():
        err_console.print(
            Panel(
                "Die Pakete der Oberflaeche fehlen noch.\n\n"
                "Bitte einmalig ausfuehren:\n"
                "  [bold]cd frontend[/bold]\n"
                f"  [bold]{npm_befehl()} install[/bold]\n"
                "  [bold]cd ..[/bold]",
                title="Noch ein Schritt fehlt",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=1)

    token = create_session_token(settings)
    adresse = startadresse(settings, token, dev=True)

    try:
        vite = starte_vite(token, settings)
    except FileNotFoundError:
        err_console.print(
            f"[red]{npm_befehl()} wurde nicht gefunden.[/red] "
            "Ist Node.js installiert? https://nodejs.org"
        )
        raise typer.Exit(code=1) from None

    console.print(
        Panel(
            f"Oeffne im Browser:\n  [bold cyan]{adresse}[/bold cyan]\n\n"
            f"Server:      http://{settings.host}:{settings.port}\n"
            f"Workspace:   {settings.workspace_path}\n\n"
            "[yellow]Der Link enthaelt dein Sitzungs-Token - ohne ihn antwortet\n"
            "Jarvis nicht. Nach jedem Neustart gibt es ein neues Token.[/yellow]\n\n"
            "Beenden mit Strg+C.",
            title="Jarvis laeuft",
            border_style="green",
        )
    )

    # Auch bei einem harten Beenden (geschlossenes Terminal, "taskkill")
    # soll Vite mitgehen. Strg+C loest ohnehin KeyboardInterrupt aus, aber
    # ein SIGTERM wuerde Python ohne das hier einfach abschiessen - und
    # Vite bliebe als unsichtbarer Prozess auf Port 5173 zurueck.
    def _beenden(signalnummer: int, rahmen: object) -> None:
        raise KeyboardInterrupt

    with contextlib.suppress(ValueError, AttributeError, OSError):
        signal.signal(signal.SIGTERM, _beenden)

    try:
        _serve(settings, token)
    except KeyboardInterrupt:
        console.print("\n[dim]Beende Jarvis ...[/dim]")
    finally:
        beende_vite(vite)


if __name__ == "__main__":  # pragma: no cover
    app()
