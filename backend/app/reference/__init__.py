"""Reference data: the size graph the engine serves (PRD §8).

Brands and size charts come from the v3 harvested data set (data/v3, imported
by v3_import): most charts are taken from brands' own published size guides,
the rest are derived from EN 13402-3 and carry confidence=low and
source_type=derived_from_standard (PRD §8.5). Conversion and base tables are
rendered from the standards module (public/commodity layer, PRD §8.7).
"""

DATA_VERSION = "v3.0"
