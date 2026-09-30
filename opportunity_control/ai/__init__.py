"""Generación gobernada de borradores sin autoridad de decisión."""

from .local import LocalGovernedDraftGenerator
from .models import AIDraft

__all__ = ["AIDraft", "LocalGovernedDraftGenerator"]
