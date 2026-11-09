from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class OrderCreate(BaseModel):
    """Request schema for creating a new order."""

    client_name: str = Field(
        min_length=2,
        max_length=120,
        description="Client name.",
    )

    gr_liv_area: float = Field(
        gt=0,
        le=10_000,
        description="Above-ground living area in square feet.",
    )

    total_bsmt_sf: float = Field(
        ge=0,
        le=10_000,
        description="Total basement area in square feet.",
    )

    garage_area: float = Field(
        ge=0,
        le=2_000,
        description="Garage area in square feet.",
    )

    year_built: int = Field(
        ge=1872,
        le=2010,
        description="Original construction year.",
    )

    overall_qual: int = Field(
        ge=1,
        le=10,
        description="Overall material and finish quality, rated from 1 to 10.",
    )

    ms_zoning: str = Field(
        min_length=1,
        max_length=10,
        description="General zoning classification.",
    )


class OrderUpdate(BaseModel):
    """Request schema for updating an existing order."""

    model_config = {"extra": "forbid"}
    client_name: str = Field(
        default=None,
        min_length=2,
        max_length=120,
        description="Updated client name.",
    )

    gr_liv_area: float = Field(default=None, gt=0, le=10_000, description="Updated living area")
    total_bsmt_sf: float = Field(default=None, ge=0, le=10_000, description="Updated basement sf")
    garage_area: float = Field(default=None, ge=0, le=2_000, description="Updated garage area")
    year_built: int = Field(default=None, ge=1872, le=2010, description="Updated year built")
    overall_qual: int = Field(default=None, ge=1, le=10, description="Updated overall_qual")
    ms_zoning: str = Field(default=None, min_length=1, max_length=10, description="Updated ms_zoning")


class OrderRead(BaseModel):
    """Response schema representing an order."""

    model_config = {"from_attributes": True}

    id: int
    client_name: str

    gr_liv_area: float
    total_bsmt_sf: float
    garage_area: float
    year_built: int
    overall_qual: int
    ms_zoning: str

    predicted_price: float | None
    prediction_status: Literal["ok", "failed", "pending"] = "pending"
    created_at: datetime


