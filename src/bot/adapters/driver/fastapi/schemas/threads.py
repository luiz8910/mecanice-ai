from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ThreadStatus = Literal["open", "awaiting_seller_response", "offer_received", "closed"]
RequestStatus = Literal["created", "processing", "ready_for_quote"]
MessageType = Literal["text", "system", "request_summary", "offer_notice"]
OfferStatus = Literal["DRAFT", "SUBMITTED_OPTIONS", "FINALIZED_QUOTE", "proposal_sent", "CANCELLED"]
OfferItemSourceType = Literal["suggested", "manual"]


class VehicleSchema(BaseModel):
    plate: str | None = None
    brand: str | None = None
    model: str | None = None
    year: str | None = None
    engine: str | None = None
    version: str | None = None
    notes: str | None = None


class WorkshopSummarySchema(BaseModel):
    id: int
    name: str
    phone: str | None = None
    address: str | None = None


class RequestedItemCreateSchema(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    part_number: str | None = Field(default=None, max_length=255)
    quantity: int = Field(..., gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class RequestedItemResponseSchema(BaseModel):
    id: int
    request_id: int
    description: str
    part_number: str | None = None
    quantity: int
    notes: str | None = None
    created_at: datetime


class ThreadCreateSchema(BaseModel):
    requested_items: list[RequestedItemCreateSchema] = Field(..., min_length=1)
    vehicle: VehicleSchema | None = None
    generate_suggestions: bool = False

    # Legacy compatibility fields.
    original_description: str | None = Field(default=None, min_length=1, max_length=4000)
    part_number: str | None = Field(default=None, max_length=255)
    requested_items_count: int | None = Field(default=None, gt=0)
    vehicle_plate: str | None = None
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: str | None = None
    vehicle_engine: str | None = None
    vehicle_version: str | None = None
    vehicle_notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        requested_items = payload.get("requested_items")
        if not requested_items:
            original_description = payload.get("original_description")
            if not original_description:
                raise ValueError("requested_items or original_description is required")
            payload["requested_items"] = [
                {
                    "description": original_description,
                    "part_number": payload.get("part_number"),
                    "quantity": payload.get("requested_items_count") or 1,
                    "notes": None,
                }
            ]

        if payload.get("vehicle") is None:
            vehicle = {
                "plate": payload.get("vehicle_plate"),
                "brand": payload.get("vehicle_brand"),
                "model": payload.get("vehicle_model"),
                "year": payload.get("vehicle_year"),
                "engine": payload.get("vehicle_engine"),
                "version": payload.get("vehicle_version"),
                "notes": payload.get("vehicle_notes"),
            }
            if any(value is not None for value in vehicle.values()):
                payload["vehicle"] = vehicle

        return payload


class ThreadMessageCreateSchema(BaseModel):
    type: MessageType = "text"
    body: str = Field(..., min_length=1, max_length=4000)


class OfferItemCreateSchema(BaseModel):
    requested_item_id: int | None = Field(default=None, gt=0)
    source_type: OfferItemSourceType
    suggested_part_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    brand: str | None = None
    part_number: str | None = None
    quantity: int = Field(default=1, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    notes: str | None = None
    compatibility_note: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    is_final_choice: bool = False

    @model_validator(mode="after")
    def normalize_aliases(self) -> "OfferItemCreateSchema":
        if self.description is None and self.title is not None:
            self.description = self.title
        if self.notes is None and self.compatibility_note is not None:
            self.notes = self.compatibility_note
        return self


class OfferItemUpdateSchema(BaseModel):
    requested_item_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    brand: str | None = None
    part_number: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    notes: str | None = None
    compatibility_note: str | None = None
    metadata_json: dict[str, Any] | None = None
    is_final_choice: bool | None = None

    @model_validator(mode="after")
    def normalize_aliases(self) -> "OfferItemUpdateSchema":
        if self.description is None and self.title is not None:
            self.description = self.title
        if self.notes is None and self.compatibility_note is not None:
            self.notes = self.compatibility_note
        return self


class OfferFinalizeSchema(BaseModel):
    selected_option_ids: list[int] | None = None


class OfferSubmitSchema(BaseModel):
    close_quote: bool = False
    selected_option_ids: list[int] | None = None


class ThreadSummarySchema(BaseModel):
    id: int
    mechanic_id: int
    workshop_id: int
    status: ThreadStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    request_id: int
    original_description: str
    part_number: str | None = None
    requested_items_count: int
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: str | None = None
    request_status: RequestStatus
    workshop_name: str
    mechanic_name: str
    submitted_offer_count: int


class ThreadCoreSchema(BaseModel):
    id: int
    mechanic_id: int
    workshop_id: int
    status: ThreadStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    vehicle_plate: str | None = None
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: str | None = None
    vehicle_engine: str | None = None
    vehicle_version: str | None = None
    vehicle_notes: str | None = None


class PartRequestResponseSchema(BaseModel):
    id: int
    thread_id: int
    original_description: str
    requested_items_count: int
    part_number: str | None = None
    vehicle_plate: str | None = None
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: str | None = None
    vehicle_engine: str | None = None
    vehicle_version: str | None = None
    vehicle_notes: str | None = None
    status: RequestStatus
    created_at: datetime
    vehicle: VehicleSchema | None = None
    requested_items: list[RequestedItemResponseSchema] = Field(default_factory=list)


class ThreadMessageResponseSchema(BaseModel):
    id: int
    thread_id: int
    sender_role: str
    sender_user_ref: str | None = None
    type: MessageType
    body: str
    metadata_json: dict[str, Any]
    created_at: datetime


class SuggestedPartResponseSchema(BaseModel):
    id: int
    thread_id: int
    request_id: int
    requested_item_id: int | None = None
    title: str
    brand: str | None = None
    part_number: str | None = None
    confidence: float | None = None
    note: str | None = None
    metadata_json: dict[str, Any]
    created_at: datetime


class OfferItemResponseSchema(BaseModel):
    id: int
    offer_id: int
    requested_item_id: int | None = None
    source_type: OfferItemSourceType
    suggested_part_id: int | None = None
    description: str
    title: str
    brand: str | None = None
    part_number: str | None = None
    quantity: int
    unit_price: float | None = None
    notes: str | None = None
    compatibility_note: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    is_final_choice: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class OfferGroupResponseSchema(BaseModel):
    requested_item_id: int
    requested_item_description: str
    requested_quantity: int
    options: list[OfferItemResponseSchema] = Field(default_factory=list)


class SellerStoreSchema(BaseModel):
    id: int
    name: str


class SellerUserSchema(BaseModel):
    id: int
    name: str


class OfferResponseSchema(BaseModel):
    id: int
    thread_id: int
    seller_id: int
    seller_shop_id: int
    status: OfferStatus
    notes: str | None = None
    summary_text: str | None = None
    final_total: float | None = None
    total_amount: float | None = None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    finalized_at: datetime | None = None
    seller_name: str
    seller_shop_name: str
    seller_store: SellerStoreSchema
    seller_user: SellerUserSchema
    groups: list[OfferGroupResponseSchema] = Field(default_factory=list)
    items: list[OfferItemResponseSchema] = Field(default_factory=list)


class OfferSubmitResponseSchema(OfferResponseSchema):
    offer_id: int
    thread_status: ThreadStatus | None = None
    service_order_id: str | None = None


class ThreadDetailResponseSchema(BaseModel):
    thread: ThreadCoreSchema
    workshop: WorkshopSummarySchema | None = None
    vehicle: VehicleSchema | None = None
    requested_items: list[RequestedItemResponseSchema] = Field(default_factory=list)
    request: PartRequestResponseSchema
    messages: list[ThreadMessageResponseSchema]
    suggestions: list[SuggestedPartResponseSchema]
    offers: list[OfferResponseSchema]


class OfferComparisonSchema(BaseModel):
    offer_id: int
    seller_id: int
    seller_name: str
    seller_shop_id: int
    seller_shop_name: str
    status: OfferStatus
    summary_text: str | None = None
    final_total: float | None = None
    total_amount: float | None = None
    submitted_at: datetime | None = None
    finalized_at: datetime | None = None
    groups: list[OfferGroupResponseSchema] = Field(default_factory=list)
    items: list[OfferItemResponseSchema] = Field(default_factory=list)
    notes: str | None = None


class ThreadComparisonResponseSchema(BaseModel):
    thread_id: int
    vehicle: VehicleSchema | None = None
    requested_items: list[RequestedItemResponseSchema] = Field(default_factory=list)
    request: PartRequestResponseSchema
    offers: list[OfferComparisonSchema]
