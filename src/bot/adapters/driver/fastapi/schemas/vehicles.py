"""Wire schemas for manufacturers and vehicles CRUD."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

BodyType = Literal[
    "hatchback", "sedan", "pickup", "suv",
    "minivan", "coupe", "van", "wagon", "convertible",
]
FuelType = Literal["flex", "gasoline", "diesel", "hybrid", "electric", "cng"]


# ── Manufacturer schemas ──────────────────────────────────────────────

class ManufacturerCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country_of_origin: str = Field(..., min_length=1, max_length=100)


class ManufacturerUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    country_of_origin: Optional[str] = Field(None, min_length=1, max_length=100)


class ManufacturerResponseSchema(BaseModel):
    id: int
    name: str
    country_of_origin: str
    created_at: datetime
    updated_at: datetime


# ── Vehicle schemas ───────────────────────────────────────────────────

class VehicleCreateSchema(BaseModel):
    manufacturer_id: int
    model: str = Field(..., min_length=1, max_length=100)
    model_year_start: int = Field(..., ge=1900, le=2100)
    model_year_end: Optional[int] = Field(None, ge=1900, le=2100)
    body_type: BodyType
    fuel_type: FuelType = "flex"
    engine_displacement: Optional[str] = Field(None, max_length=50)

    @field_validator("model_year_end")
    @classmethod
    def end_after_start(cls, v: int | None, info: object) -> int | None:
        if v is None:
            return v
        start = getattr(info, "data", {}).get("model_year_start")
        if start is not None and v < start:
            raise ValueError("model_year_end must be >= model_year_start")
        return v


class VehicleUpdateSchema(BaseModel):
    manufacturer_id: Optional[int] = None
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    model_year_start: Optional[int] = Field(None, ge=1900, le=2100)
    model_year_end: Optional[int] = Field(None, ge=1900, le=2100)
    body_type: Optional[BodyType] = None
    fuel_type: Optional[FuelType] = None
    engine_displacement: Optional[str] = Field(None, max_length=50)


class VehicleResponseSchema(BaseModel):
    id: int
    manufacturer_id: int
    manufacturer_name: str
    country_of_origin: str
    model: str
    model_year_start: int
    model_year_end: Optional[int] = None
    body_type: str
    fuel_type: str
    engine_displacement: Optional[str] = None
    created_at: datetime
    updated_at: datetime
