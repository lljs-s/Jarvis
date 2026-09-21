"""Der lokale Web-Server: uebersetzt HTTP in Aufrufe des Kerns.

Hier steht bewusst KEINE Fachlogik. Wer etwas koennen will, fragt core/ -
und laeuft damit automatisch durch dieselben Sicherheitspruefungen wie die
CLI.
"""

from .app import create_app

__all__ = ["create_app"]
