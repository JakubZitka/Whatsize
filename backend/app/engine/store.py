"""In-memory chart store. Size charts are small (tens of thousands of rows) and
read-mostly, so the whole size graph is held in memory for sub-millisecond
lookups (NFR: < 300 ms p95 from a warm cache)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.reference.catalog import CATEGORY_BY_CODE


@dataclass
class ChartStore:
    version: str
    brands: dict[str, dict]
    categories: dict[str, dict] = field(default_factory=lambda: dict(CATEGORY_BY_CODE))
    _charts: dict[tuple[str, str, str], list[dict]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, version: str, brands: list[dict], rows: list[dict]) -> ChartStore:
        charts: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for row in rows:
            charts[(row["brand_id"], row["category_code"], row["fit_code"])].append(row)
        for chart in charts.values():
            chart.sort(key=lambda r: r["size_sort"])
        store = cls(version=version, brands={b["brand_id"]: b for b in brands})
        store._charts = dict(charts)
        return store

    @classmethod
    def from_dataset(cls, dataset: dict) -> ChartStore:
        return cls.from_rows(dataset["version"], dataset["tables"]["dim_brand"],
                             dataset["tables"]["fact_brand_size_chart"])

    def brand_categories(self, brand_id: str) -> list[str]:
        cats = {c for (b, c, _f) in self._charts if b == brand_id}
        return [c for c in CATEGORY_BY_CODE if c in cats]

    def fits(self, brand_id: str, category_code: str) -> list[str]:
        return [f for (b, c, f) in self._charts if b == brand_id and c == category_code]

    def chart(self, brand_id: str, category_code: str, fit_code: str) -> list[dict]:
        return self._charts.get((brand_id, category_code, fit_code), [])

    def vanity_offset(self, brand_id: str, category_code: str) -> float:
        """Calibrated label drift applies to waist-keyed garments (PRD §8.6)."""
        if self.categories[category_code]["primary_dimension"] != "waist_cm":
            return 0.0
        return float(self.brands[brand_id].get("vanity_offset_waist_cm") or 0.0)

    @property
    def row_count(self) -> int:
        return sum(len(rows) for rows in self._charts.values())
