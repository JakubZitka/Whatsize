"""Database schema. Mirrors the WhatSize_SizingDataModel_v1 workbook.

Public / commodity layer (PRD §8.7): dimension, chart and reference tables.
Private / proprietary layer: brand_calibration (vanity offsets) — never
exposed as raw data; it only feeds the engine.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DimBrand(Base):
    __tablename__ = "dim_brand"
    brand_id = Column(String(64), primary_key=True)
    brand_name = Column(String(128), nullable=False)
    parent_group = Column(String(128))
    country = Column(String(8))
    segment = Column(String(32))
    gender_focus = Column(String(1))
    women_size_system = Column(String(16))
    men_size_system = Column(String(16))
    shirt_system = Column(String(16))
    bra_system = Column(String(16))
    shoe_grid = Column(String(16))
    shoe_us_w_offset = Column(Float)
    shoe_us_uk_offset = Column(Float)
    website = Column(String(256))
    cee_presence = Column(String(32))
    ingest_priority = Column(String(4))
    publisher_guide_url = Column(String(512))
    categories = Column(Text)


class DimGarmentCategory(Base):
    __tablename__ = "dim_garment_category"
    category_code = Column(String(16), primary_key=True)
    gender = Column(String(1), nullable=False)
    name_en = Column(String(64))
    name_cs = Column(String(64))
    kind = Column(String(16))
    primary_dimension = Column(String(64), nullable=False)
    secondary_dimensions = Column(String(128))
    silhouette_zone = Column(String(16))


class DimMeasurementPoint(Base):
    __tablename__ = "dim_measurement_point"
    code = Column(String(32), primary_key=True)
    name_en = Column(String(64))
    name_cs = Column(String(64))
    iso_8559_1_group = Column(String(16))
    unit = Column(String(4))
    self_measurable = Column(Boolean)
    maps_to_dimension = Column(String(32))
    how_to_measure = Column(Text)


class DimSizeSystem(Base):
    __tablename__ = "dim_size_system"
    code = Column(String(16), primary_key=True)
    name = Column(String(64))
    applies_to = Column(String(64))
    value_type = Column(String(16))
    conversion_rule = Column(Text)
    traps = Column(Text)


class DimFitType(Base):
    __tablename__ = "dim_fit_type"
    fit_code = Column(String(16), primary_key=True)
    name_cs = Column(String(32))
    kind = Column(String(16))
    girth_ease_min_cm = Column(Float)
    girth_ease_max_cm = Column(Float)
    length_delta_cm = Column(Float)
    size_shift_cm = Column(Float)
    rule = Column(Text)


class FactBrandSizeChart(Base):
    __tablename__ = "fact_brand_size_chart"
    row_id = Column(Integer, primary_key=True)
    brand_id = Column(String(64), ForeignKey("dim_brand.brand_id"), nullable=False)
    category_code = Column(String(16), ForeignKey("dim_garment_category.category_code"),
                           nullable=False)
    fit_code = Column(String(16), ForeignKey("dim_fit_type.fit_code"), nullable=False)
    size_system = Column(String(16), ForeignKey("dim_size_system.code"), nullable=False)
    size_label = Column(String(32), nullable=False)
    size_sort = Column(Integer, nullable=False)
    measurement_basis = Column(String(8), nullable=False)
    bust_chest_cm_min = Column(Float)
    bust_chest_cm_max = Column(Float)
    waist_cm_min = Column(Float)
    waist_cm_max = Column(Float)
    hip_cm_min = Column(Float)
    hip_cm_max = Column(Float)
    underbust_cm_min = Column(Float)
    underbust_cm_max = Column(Float)
    neck_cm_min = Column(Float)
    neck_cm_max = Column(Float)
    stature_cm_min = Column(Float)
    stature_cm_max = Column(Float)
    foot_length_mm_min = Column(Float)
    foot_length_mm_max = Column(Float)
    inseam_options_in = Column(String(32))
    confidence = Column(String(8), nullable=False)
    source_type = Column(String(32), nullable=False)
    verification_status = Column(String(32), nullable=False)
    publisher_guide_url = Column(String(512))
    __table_args__ = (
        UniqueConstraint("brand_id", "category_code", "fit_code", "size_label",
                         name="uq_chart_label"),
        Index("ix_chart_lookup", "brand_id", "category_code", "fit_code"),
    )


class RefBaseBodyTable(Base):
    __tablename__ = "ref_base_body_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    gender = Column(String(1), nullable=False)
    size_label = Column(String(8), nullable=False)
    bust_chest_cm = Column(Float)
    waist_cm = Column(Float)
    hip_cm = Column(Float)
    neck_cm = Column(Float)
    stature_cm = Column(Float)


class RefSizeConversion(Base):
    __tablename__ = "ref_size_conversion"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family = Column(String(32), nullable=False)  # women_tops | men_tops | footwear | bra
    row_no = Column(Integer, nullable=False)
    values = Column(JSON, nullable=False)


class BrandCalibration(Base):
    """Private layer: calibrated label drift, learned from fit feedback or seeded
    from measured evidence (PRD §8.6). Never exposed through the public API."""

    __tablename__ = "brand_calibration"
    brand_id = Column(String(64), ForeignKey("dim_brand.brand_id"), primary_key=True)
    vanity_offset_waist_cm = Column(Float, nullable=False, default=0.0)
    vanity_offset_source = Column(Text)
    updated_at = Column(DateTime(timezone=True))


class ReferenceDataVersion(Base):
    __tablename__ = "reference_data_version"
    version = Column(String(32), primary_key=True)
    loaded_at = Column(DateTime(timezone=True), nullable=False)
    row_counts = Column(JSON)
