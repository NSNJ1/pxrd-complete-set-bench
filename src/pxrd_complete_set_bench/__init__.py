"""Evaluation tools for complete-phase-set review in PXRD."""

from .diagnostics import run_diagnostics
from .evaluate import evaluate, validate
from .external_panel import evaluate_external_panel

__all__ = ["evaluate", "evaluate_external_panel", "run_diagnostics", "validate"]
__version__ = "0.6.2"
