"""In-memory chart store. Size charts are small (thousands of rows) and
read-mostly, so the whole size graph is held in memory for sub-millisecond
lookups (NFR: < 300 ms p95 from a warm cache)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.reference.catalog import CATEGORY_BY_CODE

ChartKey = tuple[str, str, str, str]  # brand, category, fit, size system


@dataclass
class ChartStore:
    version: str
    brands: dict[str, dict]
    categories: dict[str, dict] = field(default_factory=lambda: dict(CATEGORY_BY_CODE))
    _charts: dict[ChartKey, list[dict]] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, version: str, brands: list[dict], rows: list[dict]) -> ChartStore:
        charts: dict[ChartKey, list[dict]] = defaultdict(list)
        for row in rows:
            key = (row["brand_id"], row["category_code"], row["fit_code"], row["size_system"])
            charts[key].append(row)
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
        cats = {c for (b, c, _f, _s) in self._charts if b == brand_id}
        return [c for c in self.categories if c in cats]

    def fits(self, brand_id: str, category_code: str) -> list[str]:
        fits = {f for (b, c, f, _s) in self._charts if b == brand_id and c == category_code}
        return sorted(fits, key=lambda f: (f != "regular", f))

    def systems(self, brand_id: str, category_code: str, fit_code: str) -> list[str]:
        """Size systems of one chart, the brand's primary system first."""
        found = [(s, len(rows)) for (b, c, f, s), rows in self._charts.items()
                 if b == brand_id and c == category_code and f == fit_code]
        preferred = self.brands.get(brand_id, {}).get("primary_size_system")
        found.sort(key=lambda x: (x[0] != preferred, -x[1], x[0]))
        return [s for s, _n in found]

    def chart(self, brand_id: str, category_code: str, fit_code: str,
              system: str | None = None) -> list[dict]:
        if system is None:
            systems = self.systems(brand_id, category_code, fit_code)
            if not systems:
                return []
            system = systems[0]
        return self._charts.get((brand_id, category_code, fit_code, system), [])

    def all_rows(self, brand_id: str, category_code: str, fit_code: str) -> list[dict]:
        return [r for s in self.systems(brand_id, category_code, fit_code)
                for r in self.chart(brand_id, category_code, fit_code, s)]

    def vanity_offset(self, brand_id: str, category_code: str, rows: list[dict]) -> float:
        """Measured label drift applies to waist-keyed garments on charts derived
        from the standard only: a brand's own body chart already encodes how its
        labels map to bodies, so applying the offset there would count it twice."""
        if self.categories[category_code]["primary_dimension"] != "waist_cm":
            return 0.0
        if not rows or any(r["source_type"] != "derived_from_standard" for r in rows):
            return 0.0
        return float(self.brands[brand_id].get("vanity_offset_waist_cm") or 0.0)

    @property
    def row_count(self) -> int:
        return sum(len(rows) for rows in self._charts.values())
