"""Der Workspace-Waechter: die einzige erlaubte Tuer zum Dateisystem.

Regel des Projekts: KEIN Code ausserhalb dieser Datei baut selbst einen Pfad
zusammen und oeffnet ihn. Jedes Werkzeug fragt hier nach einem Pfad und
bekommt entweder einen geprueften Pfad innerhalb des Workspace oder einen
WorkspaceViolation-Fehler. Damit gibt es genau eine Stelle, die richtig sein
muss - und genau eine Stelle, die man mit Tests angreifen kann.

Die Pruefung laeuft in zwei Stufen:

1. `split_relative()` - reine Textpruefung, ohne das Dateisystem anzufassen.
   Sie verhaelt sich auf jedem Betriebssystem gleich, damit unter Linux
   entwickelte Tests genau das pruefen, was unter Windows passiert.
2. `Workspace.resolve()` - loest den geprueften Pfad auf und prueft danach
   erneut, ob das Ergebnis wirklich im Workspace liegt. Erst hier werden
   Symlinks und (unter Windows) Junctions aufgeloest.

Abgewehrt werden unter anderem:
  * "../../etc/passwd"          Path Traversal
  * "/etc/passwd"               absolute Unix-Pfade
  * "C:\\Windows\\system.ini"   absolute Windows-Pfade, auch unter Linux
  * "C:notizen.txt"             laufwerksrelative Windows-Pfade
  * "\\\\server\\freigabe\\x"   UNC-/Netzwerkpfade
  * "~/.ssh/id_rsa"             Home-Verzeichnis
  * "CON", "nul.txt", "COM1"    unter Windows reservierte Geraetenamen
  * "bericht.txt."  "ordner "   Punkt/Leerzeichen am Ende (Windows kuerzt sie weg)
  * "datei.txt:geheim"          Alternate Data Streams
  * Symlinks und Junctions, die aus dem Workspace hinauszeigen
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .errors import WorkspaceViolation

# Namen, die Windows fuer Geraete reserviert. Eine Datei so zu nennen fuehrt
# dort zu sehr merkwuerdigem Verhalten (NUL verschluckt alles, CON liest von
# der Tastatur) - deshalb blocken wir sie ueberall, damit sich Windows und
# Linux gleich verhalten.
RESERVED_WINDOWS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

# Zeichen, die Windows in Dateinamen verbietet. ':' faengt zusaetzlich
# Alternate Data Streams ab ("datei.txt:versteckt"), '*' und '?' verhindern,
# dass ein Modell Platzhalter statt echter Namen schickt.
FORBIDDEN_CHARS = frozenset('<>:"|?*')


def split_relative(relative: str) -> list[str]:
    """Prueft eine Pfadangabe rein textlich und zerlegt sie in Bestandteile.

    Ohne Dateisystemzugriff - und ohne Rueckfrage beim Betriebssystem.
    Ein leerer Rueckgabewert bedeutet "der Workspace-Ordner selbst".

    Wirft WorkspaceViolation, sobald etwas auch nur nach einem Ausbruch
    aussieht.
    """
    if not isinstance(relative, str):
        raise WorkspaceViolation(f"Pfad muss Text sein, nicht {type(relative).__name__}")

    if "\x00" in relative:
        raise WorkspaceViolation("Pfad enthaelt ein Null-Byte")

    # Steuerzeichen (Zeilenumbruch, Tabulator, ...) haben in Dateinamen
    # nichts zu suchen und verwirren jede Anzeige.
    for char in relative:
        if ord(char) < 32:
            raise WorkspaceViolation(f"Pfad enthaelt ein Steuerzeichen: {relative!r}")

    # Bewusst KEIN .strip() auf der ganzen Angabe: " bericht.txt " soll
    # auffallen und nicht stillschweigend zu "bericht.txt" werden. Genau
    # diese Kuerzung macht Windows naemlich selbst - und wer sie mitschickt,
    # will meistens etwas verschleiern.
    raw = relative.replace("\\", "/")
    if raw in ("", ".", "./"):
        return []

    # Absolute und laufwerksrelative Pfade: "/etc/passwd", "C:/Windows",
    # "C:notizen.txt" und UNC-Pfade "//server/freigabe". PureWindowsPath
    # erkennt alle diese Formen auch dann, wenn wir unter Linux laufen.
    windows_view = PureWindowsPath(raw)
    if windows_view.drive:
        raise WorkspaceViolation(
            f"Laufwerks- oder Netzwerkpfade sind verboten: {relative!r}. "
            "Gib den Pfad relativ zum Workspace an, z. B. 'notizen/todo.txt'."
        )
    if windows_view.root or raw.startswith("/"):
        raise WorkspaceViolation(
            f"Absolute Pfade sind verboten: {relative!r}. "
            "Gib den Pfad relativ zum Workspace an, z. B. 'notizen/todo.txt'."
        )

    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        _check_part(part, relative)
        parts.append(part)
    return parts


def _check_part(part: str, original: str) -> None:
    """Prueft einen einzelnen Pfadbestandteil (einen Ordner- oder Dateinamen)."""
    if part == "..":
        raise WorkspaceViolation(
            f"'..' ist verboten (Ausbruchsversuch aus dem Workspace): {original!r}"
        )
    if part.startswith("~"):
        raise WorkspaceViolation(f"'~' ist verboten: {original!r}")

    bad = sorted(set(part) & FORBIDDEN_CHARS)
    if bad:
        hinweis = " (Alternate Data Stream)" if ":" in bad else ""
        raise WorkspaceViolation(
            f"Unter Windows verbotenes Zeichen {''.join(bad)!r} in {part!r}{hinweis}"
        )

    # Windows entfernt Punkte und Leerzeichen am Ende stillschweigend:
    # "bericht.txt." landet in "bericht.txt", "ordner " in "ordner".
    # Wer so etwas schickt, koennte damit eine Pruefung umgehen wollen -
    # also lehnen wir es ab, statt zu raten.
    if part != part.rstrip(". "):
        raise WorkspaceViolation(
            f"Name endet auf Punkt oder Leerzeichen, das kuerzt Windows weg: {part!r}"
        )
    if part != part.strip():
        raise WorkspaceViolation(f"Name beginnt oder endet mit Leerzeichen: {part!r}")

    # Reservierte Geraetenamen gelten in Windows auch mit Endung:
    # "NUL", "nul.txt" und "CoM1.log" sind alle gesperrt.
    stem = part.split(".")[0].rstrip(" ").upper()
    if stem in RESERVED_WINDOWS_NAMES:
        raise WorkspaceViolation(
            f"Unter Windows reservierter Geraetename: {part!r}. Nimm einen anderen Namen."
        )


@dataclass(frozen=True)
class Workspace:
    """Ein fester Ordner, aus dem kein Werkzeug herauskommt.

    `root` ist immer ein absoluter, aufgeloester Pfad (keine Symlinks und
    keine Junctions mehr).
    """

    root: Path

    # -- Erzeugen ---------------------------------------------------------

    @classmethod
    def open(cls, root: str | Path) -> Workspace:
        """Oeffnet (und erstellt bei Bedarf) den Workspace-Ordner."""
        path = Path(root).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise WorkspaceViolation(
                f"Workspace-Ordner laesst sich nicht anlegen: {path}\n  Grund: {exc}"
            ) from exc
        resolved = path.resolve(strict=True)
        if not resolved.is_dir():
            raise WorkspaceViolation(f"Workspace ist kein Ordner: {resolved}")
        return cls(root=resolved)

    # -- Pruefen ----------------------------------------------------------

    def resolve(self, relative: str) -> Path:
        """Wandelt eine Nutzer-/Modellangabe in einen sicheren Pfad um.

        Die Datei muss (noch) nicht existieren - sonst koennte man nie etwas
        Neues anlegen. Wirft WorkspaceViolation bei jedem Ausbruchsversuch.
        """
        parts = split_relative(relative)
        if not parts:
            return self.root

        candidate = self.root.joinpath(*parts)

        # resolve() folgt Symlinks und unter Windows auch Junctions.
        # Zeigt eine solche Verknuepfung nach draussen, faellt das hier auf.
        real = candidate.resolve()
        if not self.contains(real):
            raise WorkspaceViolation(f"Pfad zeigt aus dem Workspace heraus: {relative!r} -> {real}")
        return real

    def contains(self, path: Path) -> bool:
        """Liegt `path` im Workspace (oder ist es der Workspace selbst)?

        Nutzt os.path.commonpath statt Textvergleich, damit unter Windows
        die Gross-/Kleinschreibung keine Rolle spielt und "workspace_alt"
        nicht faelschlich als Unterordner von "workspace" durchgeht.
        """
        try:
            common = os.path.commonpath([str(self.root), str(path)])
        except ValueError:
            # Verschiedene Laufwerke (C: vs. D:) - kein gemeinsamer Pfad.
            return False
        return os.path.normcase(common) == os.path.normcase(str(self.root))

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
            # Verknuepfungen werden nicht gelistet: sie koennten nach
            # draussen zeigen, und wer sie liest, geht ueber resolve().
            if path.is_symlink():
                continue
            if path.is_file():
                found.append(path)
        return found
