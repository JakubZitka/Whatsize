"""Body reference grids and label conversion rules.

Sources (all to be re-verified against the standard texts before external use):
- EN 13402-3 body measurement intervals and letter-code bands.
- German DOB size table for the women's base grid (bust/2 - 6 rule).
- Regional label offsets as commonly published in retail conversion tables.
"""

from __future__ import annotations

import math

# --------------------------------------------------------------------------
# Base body tables (ref_base_body_table_women / _men)
# --------------------------------------------------------------------------

# (DE label, bust, waist, hip) in cm. DE label = bust / 2 - 6 up to size 46,
# then the grade widens to 6 cm (EN 13402-3 widens above roughly size 46).
WOMEN_BASE: list[tuple[int, float, float, float]] = [
    (32, 76, 60, 86),
    (34, 80, 64, 90),
    (36, 84, 68, 94),
    (38, 88, 72, 97),
    (40, 92, 76, 100),
    (42, 96, 80, 103),
    (44, 100, 84, 106),
    (46, 104, 88, 109),
    (48, 110, 94, 114),
    (50, 116, 100, 119),
    (52, 122, 106, 124),
    (54, 128, 112, 129),
    (56, 134, 118, 134),
]
WOMEN_REGULAR_STATURE = 168

# Men: EU label = chest / 2, normal build drop (chest - waist) = 12 cm.
MEN_BASE: list[tuple[int, float, float, float, float]] = [
    (label, label * 2, label * 2 - 12, label * 2 + 4, label * 2 / 4 + 14)
    for label in range(44, 68, 2)
]  # (EU label, chest, waist, hip, neck)
MEN_REGULAR_STATURE = 176

# EN 13402-3 letter codes. Bands are irregular above L/XL and must be stored,
# not generated (PRD §8.1 principle 4). Lower bound inclusive, upper exclusive.
WOMEN_ALPHA_BUST: list[tuple[str, float, float]] = [
    ("XXS", 66, 74),
    ("XS", 74, 82),
    ("S", 82, 90),
    ("M", 90, 98),
    ("L", 98, 107),
    ("XL", 107, 119),
    ("XXL", 119, 131),
    ("3XL", 131, 143),
]
MEN_ALPHA_CHEST: list[tuple[str, float, float]] = [
    ("XS", 78, 86),
    ("S", 86, 94),
    ("M", 94, 102),
    ("L", 102, 110),
    ("XL", 110, 118),
    ("XXL", 118, 129),
    ("3XL", 129, 141),
]
ALPHA_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL"]

# Stature bands per proportional fit (cm).
STATURE_BANDS = {
    "W": {"petite": (148, 160), "regular": (160, 176), "tall": (176, 190)},
    "M": {"petite": (158, 170), "regular": (170, 188), "tall": (188, 202)},
}

KIDS_HEIGHTS = list(range(92, 170, 6))  # 92 … 164, label = mid height

# Numeric label offsets relative to the German scale (DE). "EU" alone is
# ambiguous: DE (bust/2 - 6) vs FR (bust/2 - 4) — PRD §8.1 principle 3.
WOMEN_NUMERIC_OFFSETS = {"EU_DE": 0, "EU_FR": 2, "IT": 6, "UK": -26, "AU": -26, "US": -30}
MEN_NUMERIC_OFFSETS = {"EU_DE": 0, "IT": 0, "UK": -10, "US": -10}

# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------


def interp(points: list[tuple[float, float]], x: float) -> float:
    """Piecewise-linear interpolation over sorted (x, y) with linear extrapolation."""
    segment = next((i for i in range(len(points) - 1) if x <= points[i + 1][0]),
                   len(points) - 2)
    (x0, y0), (x1, y1) = points[segment], points[segment + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def bands_from_centres(centres: list[float]) -> list[tuple[float, float]]:
    """Contiguous half-open bands with boundaries at midpoints (PRD §8.5).

    The first and last band extend by half the neighbouring grade.
    """
    edges = [centres[0] - (centres[1] - centres[0]) / 2]
    edges += [(a + b) / 2 for a, b in zip(centres, centres[1:], strict=False)]
    edges.append(centres[-1] + (centres[-1] - centres[-2]) / 2)
    edges = [round(e, 1) for e in edges]
    return list(zip(edges, edges[1:], strict=False))


def r1(x: float) -> float:
    return round(x, 1)


# Lookups derived from the base tables.
W_BUST_TO_WAIST = [(b, w) for _, b, w, _ in WOMEN_BASE]
W_BUST_TO_HIP = [(b, h) for _, b, _, h in WOMEN_BASE]
W_WAIST_TO_HIP = [(w, h) for _, _, w, h in WOMEN_BASE]
M_CHEST_TO_WAIST = [(c, w) for _, c, w, _, _ in MEN_BASE]
M_CHEST_TO_NECK = [(c, n) for _, c, _, _, n in MEN_BASE]
M_WAIST_TO_HIP = [(w, h) for _, _, w, h, _ in MEN_BASE]
M_NECK_TO_CHEST = [(n, c) for _, c, _, _, n in MEN_BASE]


def alpha_for(value: float, bands: list[tuple[str, float, float]]) -> str | None:
    for label, lo, hi in bands:
        if lo <= value < hi:
            return label
    return None


# --------------------------------------------------------------------------
# Women / men numeric label conversions (ref_conv_women_tops / _men_tops)
# --------------------------------------------------------------------------

JIS_WOMEN = [(5, 77), (7, 80), (9, 83), (11, 86), (13, 89), (15, 92), (17, 96), (19, 100),
             (21, 104), (23, 108)]


def jis_women_label(bust: float) -> str:
    number = min(JIS_WOMEN, key=lambda p: abs(p[1] - bust))[0]
    return f"{number}AR"


def gbt_label(stature: int, girth: float) -> str:
    return f"{stature}/{4 * round(girth / 4)}A"


def neck_in_label(neck_cm: float) -> str:
    inches = math.floor(neck_cm / 2.54 * 2 + 0.5) / 2
    return f"{inches:g}"


def women_label_to_de(label: str, system: str) -> int | None:
    if system not in WOMEN_NUMERIC_OFFSETS:
        return None
    try:
        return int(label) - WOMEN_NUMERIC_OFFSETS[system]
    except ValueError:
        return None


def men_label_to_de(label: str, system: str) -> int | None:
    if system not in MEN_NUMERIC_OFFSETS:
        return None
    try:
        return int(label) - MEN_NUMERIC_OFFSETS[system]
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Bras (ref_conv_bra). Band and cup are presentation; underbust and bust are
# the stored truth (PRD FR-2.7). Cup steps: 2.0 cm EU, 2.54 cm UK/US.
# --------------------------------------------------------------------------

BRA_EU_BANDS = list(range(60, 100, 5))  # 60 … 95
BRA_EU_CUPS = ["AA", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
# Published retail equivalences — letters diverge above D (PRD FR-2.7).
BRA_UK_CUPS = ["AA", "A", "B", "C", "D", "DD", "E", "F", "FF", "G", "GG", "H"]
BRA_US_CUPS = ["AA", "A", "B", "C", "D", "DD", "DDD", "G", "H", "I", "J", "K"]
BRA_JP_CUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]  # 2.5 cm steps


def bra_cup_diff(cup_index: int) -> tuple[float, float]:
    """Bust minus underbust interval for an EU cup (AA starts at 10 cm)."""
    lo = 10 + 2 * cup_index
    return lo, lo + 2


def bra_band(eu_band: int, system: str) -> int:
    step = (eu_band - 60) // 5
    return {
        "BRA_EU": eu_band,
        "BRA_JP": eu_band,
        "BRA_FR": eu_band + 15,
        "BRA_IT": step,
        "BRA_UK": 28 + 2 * step,
        "BRA_US": 28 + 2 * step,
        "BRA_AU": 28 + 2 * step - 22,
    }[system]


def bra_cup(cup_index: int, system: str) -> str:
    if system in ("BRA_UK", "BRA_AU"):
        return BRA_UK_CUPS[cup_index]
    if system == "BRA_US":
        return BRA_US_CUPS[cup_index]
    if system == "BRA_JP":
        return BRA_JP_CUPS[cup_index]
    return BRA_EU_CUPS[cup_index]


def bra_label(eu_band: int, cup_index: int, system: str) -> str:
    return f"{bra_band(eu_band, system)}{bra_cup(cup_index, system)}"


BRA_SYSTEMS = ["BRA_EU", "BRA_FR", "BRA_IT", "BRA_UK", "BRA_US", "BRA_AU", "BRA_JP"]

# --------------------------------------------------------------------------
# Footwear (ref_conv_footwear). Foot length in mm is the canonical key; every
# scale is rendered from it directly, never chained EU -> UK -> US (FR-2.6).
# --------------------------------------------------------------------------

PARIS_POINT_MM = 20 / 3  # EU step
BARLEYCORN_MM = 25.4 / 3  # UK/US step


def eu_to_foot_mm(eu: float) -> float:
    """EU (Paris point) = 1.5 x last length in cm; last = foot + 15 mm allowance."""
    return (eu / 1.5 - 1.5) * 10


def uk_to_foot_mm(uk: float) -> float:
    """UK adult = 3 x foot length in inches - 23 (allowance folded into the constant)."""
    return (uk + 23) / 3 * 25.4


def foot_mm_to_eu(mm: float) -> float:
    return 1.5 * (mm / 10 + 1.5)


def foot_mm_to_uk(mm: float) -> float:
    return 3 * mm / 25.4 - 23


def round_half(x: float) -> float:
    return math.floor(x * 2 + 0.5) / 2


def fmt_size(x: float) -> str:
    return f"{x:g}"


def eu_thirds_label(thirds: int) -> str:
    whole, rest = divmod(thirds, 3)
    return str(whole) if rest == 0 else f"{whole} {rest}/3"


def footwear_grid(grid: str, gender: str, us_w_offset: float, us_uk_offset: float):
    """Return [(system, label, sort, centre_mm, width_mm)] on a brand's native grid.

    Charts are stored on each brand's own grid: projecting a 6.67 mm EU grid
    onto an 8.47 mm UK grid collapses adjacent sizes (PRD FR-2.6).
    """
    women = gender == "W"
    out = []
    if grid == "EU_WHOLE":
        for i, eu in enumerate(range(35, 43) if women else range(39, 48)):
            out.append(("SHOE_EU", str(eu), i, eu_to_foot_mm(eu), PARIS_POINT_MM))
    elif grid == "EU_HALF":
        values = [x / 2 for x in (range(70, 85) if women else range(78, 95))]
        for i, eu in enumerate(values):
            out.append(("SHOE_EU", fmt_size(eu), i, eu_to_foot_mm(eu), PARIS_POINT_MM / 2))
    elif grid == "EU_THIRDS":
        thirds = range(36 * 3, 42 * 3 + 1) if women else range(40 * 3, 47 * 3 + 1)
        for i, t in enumerate(thirds):
            out.append(("SHOE_EU", eu_thirds_label(t), i, eu_to_foot_mm(t / 3), PARIS_POINT_MM / 3))
    elif grid in ("UK_WHOLE", "UK_HALF"):
        step = 1 if grid == "UK_WHOLE" else 0.5
        lo, hi = (3, 8) if women else (6, 12)
        n = int((hi - lo) / step) + 1
        for i in range(n):
            uk = lo + i * step
            out.append(("SHOE_UK", fmt_size(uk), i, uk_to_foot_mm(uk), BARLEYCORN_MM * step))
    elif grid in ("US_WHOLE", "US_HALF"):
        step = 1 if grid == "US_WHOLE" else 0.5
        lo, hi = (5, 11) if women else (7, 13)
        n = int((hi - lo) / step) + 1
        for i in range(n):
            us = lo + i * step
            us_m = us - us_w_offset if women else us
            uk = us_m - us_uk_offset
            system = "SHOE_US_W" if women else "SHOE_US_M"
            out.append((system, fmt_size(us), i, uk_to_foot_mm(uk), BARLEYCORN_MM * step))
    else:
        raise ValueError(f"unknown footwear grid {grid}")
    return out
