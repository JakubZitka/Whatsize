"""Reference size-graph tables (public layer) and brand calibration (private layer).

Revision ID: 0001
Revises:
Create Date: 2026-10-19

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dim_brand",
        sa.Column("brand_id", sa.String(64), primary_key=True),
        sa.Column("brand_name", sa.String(128), nullable=False),
        sa.Column("parent_group", sa.String(128)),
        sa.Column("country", sa.String(8)),
        sa.Column("segment", sa.String(32)),
        sa.Column("gender_focus", sa.String(1)),
        sa.Column("women_size_system", sa.String(16)),
        sa.Column("men_size_system", sa.String(16)),
        sa.Column("shirt_system", sa.String(16)),
        sa.Column("bra_system", sa.String(16)),
        sa.Column("shoe_grid", sa.String(16)),
        sa.Column("shoe_us_w_offset", sa.Float),
        sa.Column("shoe_us_uk_offset", sa.Float),
        sa.Column("website", sa.String(256)),
        sa.Column("cee_presence", sa.String(32)),
        sa.Column("ingest_priority", sa.String(4)),
        sa.Column("publisher_guide_url", sa.String(512)),
        sa.Column("categories", sa.Text),
    )
    op.create_table(
        "dim_garment_category",
        sa.Column("category_code", sa.String(16), primary_key=True),
        sa.Column("gender", sa.String(1), nullable=False),
        sa.Column("name_en", sa.String(64)),
        sa.Column("name_cs", sa.String(64)),
        sa.Column("kind", sa.String(16)),
        sa.Column("primary_dimension", sa.String(64), nullable=False),
        sa.Column("secondary_dimensions", sa.String(128)),
        sa.Column("silhouette_zone", sa.String(16)),
    )
    op.create_table(
        "dim_measurement_point",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name_en", sa.String(64)),
        sa.Column("name_cs", sa.String(64)),
        sa.Column("iso_8559_1_group", sa.String(16)),
        sa.Column("unit", sa.String(4)),
        sa.Column("self_measurable", sa.Boolean),
        sa.Column("maps_to_dimension", sa.String(32)),
        sa.Column("how_to_measure", sa.Text),
    )
    op.create_table(
        "dim_size_system",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("name", sa.String(64)),
        sa.Column("applies_to", sa.String(64)),
        sa.Column("value_type", sa.String(16)),
        sa.Column("conversion_rule", sa.Text),
        sa.Column("traps", sa.Text),
    )
    op.create_table(
        "dim_fit_type",
        sa.Column("fit_code", sa.String(16), primary_key=True),
        sa.Column("name_cs", sa.String(32)),
        sa.Column("kind", sa.String(16)),
        sa.Column("girth_ease_min_cm", sa.Float),
        sa.Column("girth_ease_max_cm", sa.Float),
        sa.Column("length_delta_cm", sa.Float),
        sa.Column("size_shift_cm", sa.Float),
        sa.Column("rule", sa.Text),
    )
    ranges = []
    for dim in ("bust_chest_cm", "waist_cm", "hip_cm", "underbust_cm", "neck_cm", "stature_cm",
                "foot_length_mm"):
        ranges += [sa.Column(f"{dim}_min", sa.Float), sa.Column(f"{dim}_max", sa.Float)]
    op.create_table(
        "fact_brand_size_chart",
        sa.Column("row_id", sa.Integer, primary_key=True),
        sa.Column("brand_id", sa.String(64), sa.ForeignKey("dim_brand.brand_id"),
                  nullable=False),
        sa.Column("category_code", sa.String(16),
                  sa.ForeignKey("dim_garment_category.category_code"), nullable=False),
        sa.Column("fit_code", sa.String(16), sa.ForeignKey("dim_fit_type.fit_code"),
                  nullable=False),
        sa.Column("size_system", sa.String(16), sa.ForeignKey("dim_size_system.code"),
                  nullable=False),
        sa.Column("size_label", sa.String(32), nullable=False),
        sa.Column("size_sort", sa.Integer, nullable=False),
        sa.Column("measurement_basis", sa.String(8), nullable=False),
        *ranges,
        sa.Column("inseam_options_in", sa.String(32)),
        sa.Column("confidence", sa.String(8), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("verification_status", sa.String(32), nullable=False),
        sa.Column("publisher_guide_url", sa.String(512)),
        sa.UniqueConstraint("brand_id", "category_code", "fit_code", "size_label",
                            name="uq_chart_label"),
    )
    op.create_index("ix_chart_lookup", "fact_brand_size_chart",
                    ["brand_id", "category_code", "fit_code"])
    op.create_table(
        "ref_base_body_table",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("gender", sa.String(1), nullable=False),
        sa.Column("size_label", sa.String(8), nullable=False),
        sa.Column("bust_chest_cm", sa.Float),
        sa.Column("waist_cm", sa.Float),
        sa.Column("hip_cm", sa.Float),
        sa.Column("neck_cm", sa.Float),
        sa.Column("stature_cm", sa.Float),
    )
    op.create_table(
        "ref_size_conversion",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("row_no", sa.Integer, nullable=False),
        sa.Column("values", sa.JSON, nullable=False),
    )
    op.create_table(
        "brand_calibration",
        sa.Column("brand_id", sa.String(64), sa.ForeignKey("dim_brand.brand_id"),
                  primary_key=True),
        sa.Column("vanity_offset_waist_cm", sa.Float, nullable=False, server_default="0"),
        sa.Column("vanity_offset_source", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "reference_data_version",
        sa.Column("version", sa.String(32), primary_key=True),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_counts", sa.JSON),
    )


def downgrade() -> None:
    for table in ("reference_data_version", "brand_calibration", "ref_size_conversion",
                  "ref_base_body_table", "fact_brand_size_chart", "dim_fit_type",
                  "dim_size_system", "dim_measurement_point", "dim_garment_category",
                  "dim_brand"):
        op.drop_table(table)
