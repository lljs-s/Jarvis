"""Der Workspace-Waechter: die einzige erlaubte Tuer zum Dateisystem.

Regel des Projekts: KEIN Code ausserhalb dieser Datei baut selbst einen Pfad
zusammen und oeffnet ihn. Jedes Werkzeug fragt hier nach einem Pfad und
bekommt entweder einen geprueften Pfad innerhalb des Workspace oder einen
WorkspaceViolation-Fehler. Damit gibt es genau eine Stelle, die richtig sein
muss - und genau eine Stelle, die man mit Tests angreifen kann.

Abgewehrt werden unter anderem:
  * "../../etc/passwd"        (Path Traversal)
  * "/etc/passwd"             (absolute Unix-Pfade)
  * "C:\\Windows\\system.ini"  (absolute Windows-Pfade, auch unter Linux)
  * "~/.ssh/id_rsa"           (Home-Verzeichnis)
  * ein Symlink im Workspace, der nach draussen zeigt
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .errors import WorkspaceViolation

# Namen, die Windows fuer Geraete reserviert. Eine Datei so zu nennen fuehrt
# dort zu sehr merkwuerdigem Verhalten - deshalb blocken wir sie ueberall,
# damit sich Windows und Linux gleich verhalten.
_RESERVED_WINDOWS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


@dataclass(frozen=True)
class Workspace:
    """Ein fester Ordner, aus dem kein Werkzeug herauskommt.

    `root` ist immer ein absoluter, aufgeloester Pfad (keine Symlinks mehr).
    """

    root: Path

    # -- Erzeugen ---------------------------------------------------------

    @classmethod
    def open(cls, root: str | Path) -> Workspace:
        """Oeffnet (und erstellt bei Bedarf) den Workspace-Ordner."""
        path = Path(root).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise WorkspaceViolation(f"Workspace ist kein Ordner: {resolved}")
        return cls(root=resolved)

    # -- Pruefen ----------------------------------------------------------

    def resolve(self, relative: str) -> Path:
        """Wandelt eine Nutzer-/Modellangabe in einen sicheren Pfad um.

        Wirft WorkspaceViolation, sobald etwas auch nur nach einem Ausbruch
        aussieht. Die Datei muss (noch) nicht existieren.
        """
        if not isinstance(relative, str):
            raise WorkspaceViolation(f"Pfad muss Text sein, nicht {type(relative).__name__}")

        raw = relative.strip().replace("\\", "/")
        if raw in ("", ".", "./"):
            return self.root

        if "\x00" in raw:
            raise WorkspaceViolation("Pfad enthaelt ein Null-Byte")

        # Absolute Pfade - sowohl "/etc/passwd" als auch "C:/Windows".
        # PureWindowsPath erkennt beide Formen, auch wenn wir auf Linux laufen.
        windows_view = PureWindowsPath(raw)
        if windows_view.drive or windows_view.root:
            raise WorkspaceViolation(
                f"Absolute Pfade sind verboten: {relative!r}. "
                "Gib den Pfad relativ zum Workspace an, z. B. 'notizen/todo.txt'."
            )

        parts = [p for p in raw.split("/") if p not in ("", ".")]
        for part in parts:
            if part == "..":
                raise WorkspaceViolation(
                    f"'..' ist verboten (Ausbruchsversuch aus dem Workspace): {relative!r}"
                )
            if part.startswith("~"):
                raise WorkspaceViolation(f"'~' ist verboten: {relative!r}")
            if part.split(".")[0].upper() in _RESERVED_WINDOWS_NAMES:
                raise WorkspaceViolation(f"Unter Windows reservierter Name: {part!r}")

        candidate = self.root.joinpath(*parts)

        # resolve() folgt Symlinks. Zeigt ein Symlink im Workspace nach
        # draussen, faellt das genau hier auf.
        real = candidate.resolve()
        if real != self.root and self.root not in real.parents:
            raise WorkspaceViolation(
                f"Pfad zeigt aus dem Workspace heraus: {relative!r} -> {real}"
            )
        return real

    def resolve_file(self, relative: str) -> Path:
        """Wie `resolve`, verlangt aber eine existierende Datei."""
        from .errors import ToolError  # lokal, um Ringimporte zu vermeiden

        path = self.resolve(relative)
        if not path.exists():
            raise ToolError(f"Datei nicht gefunden: {self.label(path)}")
        if not path.is_file():
            raise ToolError(f"Das ist eine Datei-Anfrage, aber {self.label(path)} ist ein Ordner.")
        return path

    # -- Anzeigen ---------------------------------------------------------

    def label(self, path: Path) -> str:
        """Pfad fuer Ausgaben: relativ zum Workspace, immer mit '/'."""
        try:
            return path.resolve().relative_to(self.root).as_posix() or "."
        except ValueError:
            return str(path)

    def iter_files(self, subdir: str = ".", limit: int = 500) -> list[Path]:
        """Listet Dateien unter `subdir` (rekursiv, alphabetisch, begrenzt)."""
        start = self.resolve(subdir)
        if not start.is_dir():
            return [start] if start.is_file() else []
        found: list[Path] = []
        for path in sorted(start.rglob("*")):
            if len(found) >= limit:
                break
            if path.is_file() and not path.is_symlink():
                found.append(path)
        return found
