"""Small helpers for deriving element sets from frozen phase labels."""

from __future__ import annotations

import re

ELEMENTS = {
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
}


def phase_elements(source: str, phase_id: str) -> tuple[str, ...] | None:
    """Return the element set encoded in a frozen phase label, when available."""
    if source == "ariadnex_controlled":
        return {
            "A": ("Ca", "C", "O"),
            "B": ("Zn", "O"),
            "C": ("Ti", "O"),
            "D": ("Sn", "O"),
        }.get(phase_id)
    if source == "rare_earth_mof":
        return None
    formula = phase_id.split("_", 1)[0]
    if source == "xca_nicoal":
        formula = re.sub(r"\s+mart\.?.*$", "", formula)
    symbols = tuple(
        dict.fromkeys(
            symbol
            for symbol in re.findall(r"[A-Z][a-z]?", formula)
            if symbol in ELEMENTS
        )
    )
    return symbols or None
