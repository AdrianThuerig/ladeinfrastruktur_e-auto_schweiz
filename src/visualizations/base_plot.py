"""
base_plot.py
============
Abstrakte Basisklasse für alle Plot-Klassen.
"""
from abc import ABC, abstractmethod


class BasePlot(ABC):
    """Abstrakte Basisklasse mit standardisiertem Interface für alle Plots."""

    @abstractmethod
    def render(self):
        """Erzeugt und gibt die Visualisierung zurück."""
        pass
