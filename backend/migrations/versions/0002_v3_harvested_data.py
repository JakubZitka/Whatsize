"""v3 harvested size graph: provenance, new dimensions, several systems per chart.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BRAND_COLUMNS = [
    ("primary_size_system", sa.String(16)),
    ("data_source", sa.String(32)),
    ("brand_confidence", sa.String(16)),
    ("harvest_status", sa.String(32)),
    ("harvest_note", sa.Text),
    ("market_of_chart", sa.Text),
]
CHART_COLUMNS = [
    ("inside_leg_cm_min", sa.Float),
    ("inside_leg_cm_max", sa.Float),
    ("sleeve_cm_min", sa.Float),
    ("sleeve_cm_max", sa.Float),
    ("band_type", sa.String(32)),
    ("market", sa.Text),
    ("source_chart_id", sa.String(16)),
]


def upgrade() -> None:
    with op.batch_alter_table("dim_brand") as batch:
        for name, type_ in BRAND_COLUMNS:
            batch.add_column(sa.Column(name, type_))
    with op.batch_alter_table("fact_brand_size_chart") as batch:
        for name, type_ in CHART_COLUMNS:
            batch.add_column(sa.Column(name, type_))
        # One brand can publish a category in several systems (e.g. 38 and M).
        batch.drop_constraint("uq_chart_label", type_="unique")
        batch.create_unique_constraint(
            "uq_chart_label_v3",
            ["brand_id", "category_code", "fit_code", "size_system", "size_label"])


def downgrade() -> None:
    with op.batch_alter_table("fact_brand_size_chart") as batch:
        batch.drop_constraint("uq_chart_label_v3", type_="unique")
        batch.create_unique_constraint(
            "uq_chart_label", ["brand_id", "category_code", "fit_code", "size_label"])
        for name, _type in reversed(CHART_COLUMNS):
            batch.drop_column(name)
    with op.batch_alter_table("dim_brand") as batch:
        for name, _type in reversed(BRAND_COLUMNS):
            batch.drop_column(name)
