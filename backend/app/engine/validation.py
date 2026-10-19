"""Measurement validation (PRD FR-1.2): the user cannot enter an invalid body.

(a) absolute plausible range — blocks;
(b) internal consistency — blocks, naming the conflicting field;
(c) statistical outlier against the reference population — warns, asks to confirm.
"""

from __future__ import annotations

from app.engine.matching import dim_name, fmt

ABSOLUTE = {
    "stature_cm": (120, 220),
    "bust_chest_cm": (60, 170),
    "underbust_cm": (55, 140),
    "waist_cm": (45, 170),
    "hip_cm": (60, 180),
    "neck_cm": (25, 60),
    "foot_length_mm": (180, 340),
}

# Approximate adult population (mean, sd). Placeholder until replaced with
# anthropometric survey data for the launch markets.
POPULATION = {
    "W": {"stature_cm": (166, 7), "bust_chest_cm": (92, 10), "underbust_cm": (77, 8),
          "waist_cm": (76, 11), "hip_cm": (101, 10), "foot_length_mm": (240, 12)},
    "M": {"stature_cm": (179, 7), "bust_chest_cm": (101, 9), "waist_cm": (90, 12),
          "hip_cm": (101, 8), "neck_cm": (39.5, 2.5), "foot_length_mm": (267, 13)},
}


def validate(measurements: dict, gender: str) -> dict:
    m = {k: float(v) for k, v in measurements.items() if v is not None}
    errors, warnings = [], []

    for dim, value in m.items():
        if dim not in ABSOLUTE:
            errors.append({"field": dim, "level": "range", "message": "Neznámý rozměr."})
            continue
        lo, hi = ABSOLUTE[dim]
        if not lo <= value <= hi:
            unit = "mm" if dim.endswith("_mm") else "cm"
            errors.append({"field": dim, "level": "range",
                           "message": f"{dim_name(dim, gender).capitalize()} musí být mezi "
                                      f"{fmt(lo)} a {fmt(hi)} {unit}."})
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    def conflict(field, other, message):
        errors.append({"field": field, "level": "consistency", "conflicts_with": other,
                       "message": message})

    if "bust_chest_cm" in m and "underbust_cm" in m:
        diff = m["bust_chest_cm"] - m["underbust_cm"]
        if diff < 2:
            conflict("bust_chest_cm", "underbust_cm",
                     "Obvod přes prsa musí být větší než obvod pod prsy. Měř pod prsy těsně, "
                     "přes prsa volně.")
        elif diff > 45:
            conflict("bust_chest_cm", "underbust_cm",
                     f"Rozdíl přes prsa a pod prsy {fmt(diff)} cm je neobvykle velký — "
                     "zkontroluj obě hodnoty.")
    if "hip_cm" in m and "waist_cm" in m:
        diff = m["hip_cm"] - m["waist_cm"]
        if not -25 <= diff <= 60:
            conflict("hip_cm", "waist_cm",
                     f"Rozdíl boků a pasu {fmt(diff)} cm je mimo lidský rozsah — zkontroluj, "
                     "že pas měříš v nejužším místě a boky v nejširším.")
    if "neck_cm" in m and "bust_chest_cm" in m:
        ratio = m["neck_cm"] / m["bust_chest_cm"]
        if not 0.28 <= ratio <= 0.52:
            conflict("neck_cm", "bust_chest_cm",
                     "Obvod krku neodpovídá obvodu hrudníku — zkontroluj obě hodnoty.")
    if "foot_length_mm" in m and "stature_cm" in m:
        ratio = m["foot_length_mm"] / 10 / m["stature_cm"]
        if not 0.12 <= ratio <= 0.18:
            conflict("foot_length_mm", "stature_cm",
                     "Délka chodidla neodpovídá výšce — měříš chodidlo v milimetrech?")

    for dim, value in m.items():
        mean, sd = POPULATION.get(gender, {}).get(dim, (None, None))
        if mean is not None and abs(value - mean) > 3 * sd:
            warnings.append({"field": dim,
                             "message": f"{dim_name(dim, gender).capitalize()} {fmt(value)} je "
                                        "neobvyklá hodnota. Je správně?"})
    return {"valid": not errors, "errors": errors, "warnings": warnings}
