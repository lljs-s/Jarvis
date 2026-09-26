"""Eigene Fehlertypen.

Warum eigene Fehler? Damit die CLI (und spaeter die Web-UI) genau
unterscheiden kann, WAS schiefging: ein Sandbox-Ausbruchsversuch ist etwas
voellig anderes als eine fehlende Datei oder ein API-Problem.
"""

from __future__ import annotations


class JarvisError(Exception):
    """Basisklasse fuer alle Fehler dieses Projekts."""


class ConfigError(JarvisError):
    """Etwas an der Konfiguration (.env) stimmt nicht."""


class WorkspaceViolation(JarvisError):
    """Ein Pfad zeigt aus dem Workspace heraus. Wird immer hart abgelehnt."""


class DatenschutzVerstoss(WorkspaceViolation):
    """Daten wuerden zu jemandem fliessen, der sie nicht sehen darf.

    Unterklasse von WorkspaceViolation: fuer den Agenten ist es dasselbe
    wie ein Ausbruchsversuch - hart verboten, aber kein Absturz.
    """


class ModulFehler(JarvisError):
    """Eine Aenderung am Modulbaum ist nicht moeglich (Name belegt, Ziel ungueltig ...).

    Die Meldung ist fuer den Nutzer gedacht und darf angezeigt werden.
    """


class ToolError(JarvisError):
    """Ein Werkzeug konnte seine Aufgabe nicht erledigen (z. B. Datei fehlt).

    Solche Fehler sind erwartbar: sie werden dem Modell als Fehlermeldung
    zurueckgegeben, damit es sich korrigieren kann.
    """


class ModelError(JarvisError):
    """Das Modell/die API hat nicht geantwortet oder abgelehnt."""
