from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base; tables follow the WhatSize_SizingDataModel_v1 workbook
    (dim_brand, dim_garment_category, fact_brand_size_chart, ...)."""
