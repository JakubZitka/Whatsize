"""Migrate, seed and load the reference size graph.

Idempotent: the seed is written only when reference_data_version lacks the
current DATA_VERSION. On Postgres the whole step runs under an advisory lock
so several app servers starting together cannot race (prod runs two).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, insert, select, text
from sqlalchemy.engine import Connection, Engine

from app import models as m
from app.engine.store import ChartStore
from app.reference import DATA_VERSION
from app.reference.dataset import build_dataset

log = logging.getLogger("whatsize.seed")

BACKEND_DIR = Path(__file__).resolve().parents[1]
ADVISORY_LOCK_ID = 774_211  # arbitrary, unique to this app

_SEEDED_TABLES = [m.ReferenceDataVersion, m.BrandCalibration, m.RefSizeConversion,
                  m.RefBaseBodyTable, m.FactBrandSizeChart, m.DimFitType, m.DimSizeSystem,
                  m.DimMeasurementPoint, m.DimGarmentCategory, m.DimBrand]


def _alembic_config(conn: Connection) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.attributes["connection"] = conn
    return cfg


def _columns(model) -> set[str]:
    return {c.name for c in model.__table__.columns}


def _pick(rows: list[dict], model) -> list[dict]:
    cols = _columns(model)
    return [{k: v for k, v in row.items() if k in cols} for row in rows]


def _write_seed(conn: Connection) -> dict:
    data = build_dataset()
    t = data["tables"]
    for model in _SEEDED_TABLES:
        conn.execute(delete(model))
    conn.execute(insert(m.DimBrand), _pick(t["dim_brand"], m.DimBrand))
    conn.execute(insert(m.DimGarmentCategory),
                 _pick(t["dim_garment_category"], m.DimGarmentCategory))
    conn.execute(insert(m.DimMeasurementPoint),
                 _pick(t["dim_measurement_point"], m.DimMeasurementPoint))
    conn.execute(insert(m.DimSizeSystem), _pick(t["dim_size_system"], m.DimSizeSystem))
    conn.execute(insert(m.DimFitType), _pick(t["dim_fit_type"], m.DimFitType))
    conn.execute(insert(m.FactBrandSizeChart),
                 _pick(t["fact_brand_size_chart"], m.FactBrandSizeChart))
    body = [{"gender": "W", "size_label": str(r["size_de"]), "bust_chest_cm": r["bust_cm"],
             "waist_cm": r["waist_cm"], "hip_cm": r["hip_cm"], "stature_cm": r["stature_cm"]}
            for r in t["ref_base_body_table_women"]]
    body += [{"gender": "M", "size_label": str(r["size_eu"]), "bust_chest_cm": r["chest_cm"],
              "waist_cm": r["waist_cm"], "hip_cm": r["hip_cm"], "neck_cm": r["neck_cm"],
              "stature_cm": r["stature_cm"]} for r in t["ref_base_body_table_men"]]
    conn.execute(insert(m.RefBaseBodyTable), body)
    conversions = []
    for family in ("women_tops", "men_tops", "footwear", "bra"):
        for i, row in enumerate(t[f"ref_conv_{family}"]):
            conversions.append({"family": family, "row_no": i, "values": row})
    conn.execute(insert(m.RefSizeConversion), conversions)
    now = datetime.now(UTC)
    conn.execute(insert(m.BrandCalibration), [
        {"brand_id": b["brand_id"], "vanity_offset_waist_cm": b["vanity_offset_waist_cm"],
         "vanity_offset_source": b["vanity_offset_source"] or None, "updated_at": now}
        for b in t["dim_brand"]
    ])
    counts = {name: len(rows) for name, rows in t.items()}
    conn.execute(insert(m.ReferenceDataVersion),
                 [{"version": DATA_VERSION, "loaded_at": now, "row_counts": counts}])
    return counts


def migrate_and_seed(engine: Engine) -> bool:
    """Bring the schema to head and load the seed if needed. Returns True if seeded."""
    # One transaction with a transaction-scoped lock: safe behind a connection
    # pooler (e.g. Neon's), where a session-level lock could outlive the deploy.
    with engine.connect() as conn, conn.begin():
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": ADVISORY_LOCK_ID})
        command.upgrade(_alembic_config(conn), "head")
        current = conn.execute(select(m.ReferenceDataVersion.version).where(
            m.ReferenceDataVersion.version == DATA_VERSION)).first()
        if current:
            return False
        log.info("seeding reference data %s", DATA_VERSION)
        _write_seed(conn)
        return True


def load_store(engine: Engine) -> ChartStore:
    with engine.connect() as conn:
        version = conn.execute(select(m.ReferenceDataVersion.version).order_by(
            m.ReferenceDataVersion.loaded_at.desc())).scalar()
        if version is None:
            raise RuntimeError("reference data not seeded")
        brands = [dict(r._mapping) for r in conn.execute(
            select(m.DimBrand, m.BrandCalibration.vanity_offset_waist_cm)
            .join(m.BrandCalibration, m.BrandCalibration.brand_id == m.DimBrand.brand_id,
                  isouter=True))]
        rows = [dict(r._mapping) for r in conn.execute(select(m.FactBrandSizeChart))]
    return ChartStore.from_rows(version, brands, rows)


def bundled_store() -> ChartStore:
    """The same seed, built in memory — used when the database is unavailable."""
    return ChartStore.from_dataset(build_dataset())
