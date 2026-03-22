"""Structured recommendation pipeline with conservative pre-LLM filtering."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from src.bot.application.dtos.recommendation.candidate import Candidate
from src.bot.application.dtos.recommendation.part_request import PartRequest
from src.bot.application.dtos.recommendation.recommendation_item_result import (
    RecommendationItemResult,
)
from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.recommendation_response import (
    RecommendationResponse,
)
from src.bot.application.ports.driven.llm_recommendation_port import (
    LlmRecommendationPort,
)
from src.bot.infrastructure.logging import get_logger

logger = get_logger(__name__)

DEBUG_PREFIX = "[RECOMMENDER_DEBUG]"

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "spark_plug": ("vela", "vela de ignicao", "spark plug"),
    "alternator": ("alternador",),
    "air_filter": ("filtro de ar",),
    "oil_filter": ("filtro de oleo",),
    "fuel_filter": ("filtro de combustivel",),
    "oil": ("oleo", "lubrificante", "5w30", "10w40", "15w40"),
    "bearing": ("rolamento",),
    "battery": ("bateria",),
}

CATEGORY_LABELS = {
    "spark_plug": "vela de ignicao",
    "alternator": "alternador",
    "air_filter": "filtro de ar",
    "oil_filter": "filtro de oleo",
    "fuel_filter": "filtro de combustivel",
    "oil": "oleo lubrificante",
    "bearing": "rolamento",
    "battery": "bateria",
    "unknown": "desconhecido",
}

KNOWN_BRANDS = (
    "fiat",
    "chevrolet",
    "gm",
    "volkswagen",
    "vw",
    "ford",
    "renault",
    "toyota",
    "honda",
    "hyundai",
    "nissan",
    "subaru",
    "peugeot",
    "citroen",
)

MODEL_TO_BRAND = {
    "palio": "fiat",
    "uno": "fiat",
    "vectra": "chevrolet",
    "gol": "volkswagen",
    "fox": "volkswagen",
    "celta": "chevrolet",
    "onix": "chevrolet",
}

COMPATIBILITY_MODEL_HINTS = tuple(MODEL_TO_BRAND.keys())
SENSITIVE_TYPES = {"alternator"}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _compact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "", [], {}, ())}


def _safe_json(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        return str(payload)


def _normalize_vehicle(vehicle: dict[str, Any] | None) -> dict[str, Any]:
    if not vehicle:
        return {}
    normalized: dict[str, Any] = {}
    for key in ("plate", "brand", "model", "year", "engine", "version", "notes"):
        value = vehicle.get(key)
        if value is None:
            continue
        value_text = str(value).strip()
        if value_text:
            normalized[key] = value_text
    return normalized


def _extract_years(text: str) -> list[int]:
    return [int(match.group(0)) for match in re.finditer(r"\b(19|20)\d{2}\b", text)]


def _extract_year_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for match in re.finditer(r"\b(19|20)\d{2}\s*[-/]\s*(19|20)\d{2}\b", text):
        values = re.findall(r"(?:19|20)\d{2}", match.group(0))
        if len(values) == 2:
            start, end = int(values[0]), int(values[1])
            ranges.append((min(start, end), max(start, end)))
    return ranges


def infer_item_type(text: str | None) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return "unknown"
    for item_type, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return item_type
    return "unknown"


def normalize_item_label(text: str) -> str:
    item_type = infer_item_type(text)
    return CATEGORY_LABELS.get(item_type, text.strip()) if item_type != "unknown" else text.strip()


def _maybe_extract_vehicle_from_text(
    text: str,
    structured_vehicle: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    vehicle = dict(structured_vehicle)
    conflicts: list[str] = []
    normalized_text = _normalize_text(text)

    detected_years = _extract_years(normalized_text)
    if detected_years:
        detected_year = str(detected_years[-1])
        current_year = str(vehicle.get("year") or "").strip()
        if current_year and current_year != detected_year:
            conflicts.append(f"year_text={detected_year} year_form={current_year}")
        elif not current_year:
            vehicle["year"] = detected_year

    if not vehicle.get("model"):
        for model, brand in MODEL_TO_BRAND.items():
            if model in normalized_text:
                vehicle["model"] = model.title()
                vehicle.setdefault("brand", brand.upper() if brand == "gm" else brand.title())
                break

    if not vehicle.get("brand"):
        for brand in KNOWN_BRANDS:
            if brand in normalized_text:
                vehicle["brand"] = brand.upper() if brand in {"gm", "vw"} else brand.title()
                break

    return vehicle, conflicts


def split_description_into_items(description: str) -> list[str]:
    base_description = str(description or "").strip()
    normalized = _normalize_text(base_description)
    if not base_description:
        return []
    if all(separator not in normalized for separator in (" e ", ",", ";", "/")):
        return [base_description]

    prefix = base_description
    vehicle_clause = ""
    para_match = re.search(r"\bpara\b\s+(.+)$", base_description, re.IGNORECASE)
    if para_match:
        prefix = base_description[: para_match.start()].strip()
        vehicle_clause = para_match.group(1).strip()

    pieces = re.split(r"\s*(?:,|/|;|\be\b)\s*", prefix, flags=re.IGNORECASE)
    normalized_items = [normalize_item_label(piece) for piece in pieces if piece and piece.strip()]
    typed_items = [piece for piece in normalized_items if infer_item_type(piece) != "unknown"]
    if len(typed_items) >= 2 and len(typed_items) == len(normalized_items):
        return typed_items
    if vehicle_clause:
        return [base_description]
    return [base_description]


def expand_requested_items(
    requested_items: list[dict[str, Any]],
    vehicle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    _normalize_vehicle(vehicle)
    for item in requested_items:
        description = str(item.get("description") or "").strip()
        notes = item.get("notes")
        split_items = split_description_into_items(description)
        if len(split_items) <= 1:
            expanded.append(
                {
                    "description": normalize_item_label(description) or description,
                    "part_number": item.get("part_number"),
                    "quantity": int(item.get("quantity") or 1),
                    "notes": notes,
                }
            )
            continue

        for split_item in split_items:
            expanded.append(
                {
                    "description": split_item,
                    "part_number": item.get("part_number"),
                    "quantity": int(item.get("quantity") or 1),
                    "notes": notes,
                }
            )
    return expanded


@dataclass(slots=True)
class StructuredItem:
    item_id: str
    description: str
    quantity: int
    part_number: str | None
    notes: str | None
    requested_item_type: str
    vehicle: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    raw_candidates: list[dict[str, Any]] = field(default_factory=list)


class FilteredRecommendationService(LlmRecommendationPort):
    def __init__(self, llm: LlmRecommendationPort | None = None) -> None:
        self._llm = llm

    async def generate(self, request: RecommendationRequest) -> RecommendationResponse:
        structured_vehicle = _normalize_vehicle(request.vehicle)
        raw_context = dict(request.context or {})
        items = self._build_items(request, structured_vehicle, raw_context)

        logger.info(
            "%s solicitation_text=%s form_vehicle=%s extracted_items=%s",
            DEBUG_PREFIX,
            _safe_json(raw_context.get("original_description") or [item.description for item in items]),
            _safe_json(structured_vehicle),
            _safe_json(
                [
                    {
                        "item_id": item.item_id,
                        "description": item.description,
                        "requested_item_type": item.requested_item_type,
                        "quantity": item.quantity,
                    }
                    for item in items
                ]
            ),
        )

        item_results: list[RecommendationItemResult] = []
        flattened_candidates: list[Candidate] = []
        flattened_rejections: list[Candidate] = []
        global_missing_fields: list[str] = []

        for item in items:
            accepted_candidates, rejected_candidates = self._filter_candidates(item)
            summary = self._summarize_item(item, accepted_candidates, rejected_candidates)
            needs_more_info = bool(item.missing_fields)
            final_candidates = accepted_candidates

            if accepted_candidates and not needs_more_info and self._llm is not None:
                final_candidates, llm_needs_more_info, llm_missing_fields = await self._rank_with_llm(
                    request=request,
                    item=item,
                    accepted_candidates=accepted_candidates,
                    rejected_candidates=rejected_candidates,
                )
                needs_more_info = needs_more_info or llm_needs_more_info
                for field_name in llm_missing_fields:
                    if field_name not in item.missing_fields:
                        item.missing_fields.append(field_name)

            item_result = RecommendationItemResult(
                item_id=item.item_id,
                description=item.description,
                requested_item_type=item.requested_item_type,
                vehicle=item.vehicle,
                needs_more_info=needs_more_info,
                required_missing_fields=item.missing_fields,
                accepted_candidates=final_candidates,
                rejected_candidates=rejected_candidates,
                query={
                    "requested_item_type": item.requested_item_type,
                    "vehicle": _compact_dict(item.vehicle),
                    "filters": [
                        "strict_category" if item.requested_item_type != "unknown" else "unknown_category",
                        "strict_vehicle",
                        "sensitive_missing_data" if item.missing_fields else "basic_vehicle",
                    ],
                },
                summary=summary,
            )
            item_results.append(item_result)
            flattened_candidates.extend(final_candidates)
            flattened_rejections.extend(rejected_candidates)
            for field_name in item.missing_fields:
                if field_name not in global_missing_fields:
                    global_missing_fields.append(field_name)

            logger.info(
                "%s item=%s inferred_type=%s raw_candidates=%s accepted=%s rejected=%s missing=%s summary=%s",
                DEBUG_PREFIX,
                item.item_id,
                item.requested_item_type,
                _safe_json([self._candidate_debug_view(candidate) for candidate in item.raw_candidates]),
                _safe_json([candidate.model_dump() for candidate in final_candidates]),
                _safe_json([candidate.model_dump() for candidate in rejected_candidates]),
                _safe_json(item.missing_fields),
                summary,
            )

        needs_more_info = any(item.needs_more_info for item in item_results)
        return RecommendationResponse(
            id=request.requester_id,
            requested_item_type=item_results[0].requested_item_type if len(item_results) == 1 else None,
            needs_more_info=needs_more_info,
            required_missing_fields=global_missing_fields,
            candidates=flattened_candidates,
            accepted_candidates=flattened_candidates,
            rejected_candidates=flattened_rejections,
            items=item_results,
            evidences=[],
            raw={
                "structured_vehicle": structured_vehicle,
                "item_count": len(item_results),
                "llm_used": bool(self._llm and flattened_candidates),
            },
        )

    def _build_items(
        self,
        request: RecommendationRequest,
        structured_vehicle: dict[str, Any],
        context: dict[str, Any],
    ) -> list[StructuredItem]:
        parts = list(request.parts or [])
        if not parts:
            raw_description = str(context.get("original_description") or "").strip()
            if raw_description:
                parts = [PartRequest(description=raw_description, quantity=1)]

        if not parts:
            return []

        raw_candidates_by_item = context.get("raw_candidates_by_item") or {}
        shared_raw_candidates = context.get("raw_candidates") or context.get("catalog_candidates") or []
        items: list[StructuredItem] = []

        for index, part in enumerate(parts, start=1):
            original_description = str(part.description or "").strip()
            split_descriptions = split_description_into_items(original_description) or [original_description]
            for split_index, split_description in enumerate(split_descriptions, start=1):
                item_id = part.item_id or f"item-{index}"
                if len(split_descriptions) > 1:
                    item_id = f"{item_id}-{split_index}"

                resolved_vehicle, conflicts = _maybe_extract_vehicle_from_text(
                    original_description,
                    structured_vehicle,
                )
                if conflicts:
                    logger.warning(
                        "%s vehicle_conflict item=%s conflicts=%s",
                        DEBUG_PREFIX,
                        item_id,
                        _safe_json(conflicts),
                    )
                item_type = infer_item_type(split_description)
                missing_fields = self._missing_fields_for_item(
                    item_type=item_type,
                    vehicle=resolved_vehicle,
                    part=part,
                    context=context,
                )

                raw_candidates = raw_candidates_by_item.get(item_id) or raw_candidates_by_item.get(
                    part.item_id or f"item-{index}"
                )
                if raw_candidates is None:
                    raw_candidates = shared_raw_candidates

                items.append(
                    StructuredItem(
                        item_id=item_id,
                        description=normalize_item_label(split_description) or split_description,
                        quantity=int(part.quantity or 1),
                        part_number=part.part_number,
                        notes=part.notes,
                        requested_item_type=item_type,
                        vehicle=resolved_vehicle,
                        missing_fields=missing_fields,
                        raw_candidates=list(raw_candidates or []),
                    )
                )
        return items

    def _missing_fields_for_item(
        self,
        *,
        item_type: str,
        vehicle: dict[str, Any],
        part: PartRequest,
        context: dict[str, Any],
    ) -> list[str]:
        if item_type not in SENSITIVE_TYPES:
            return []

        available = {
            "engine": vehicle.get("engine"),
            "version": vehicle.get("version"),
            "amperage": context.get("amperage") or part.metadata.get("amperage"),
            "connector": context.get("connector") or part.metadata.get("connector"),
            "pulley": context.get("pulley") or part.metadata.get("pulley"),
            "fuel": context.get("fuel") or part.metadata.get("fuel"),
            "transmission": context.get("transmission") or part.metadata.get("transmission"),
            "part_number": part.part_number,
            "photo": context.get("photo") or part.metadata.get("photo"),
        }
        present_keys = {key for key, value in available.items() if value not in (None, "", [], {})}
        if present_keys.intersection({"engine", "version", "amperage", "connector", "pulley", "part_number", "photo"}):
            return []
        return ["engine", "version", "amperage", "connector", "pulley"]

    def _candidate_debug_view(self, candidate: dict[str, Any]) -> dict[str, Any]:
        metadata = candidate.get("metadata") or candidate.get("metadata_json") or {}
        return {
            "id": candidate.get("id"),
            "part_number": candidate.get("part_number"),
            "brand": candidate.get("brand"),
            "title": candidate.get("title") or candidate.get("description"),
            "category": candidate.get("category") or metadata.get("category"),
            "compatibility_notes": metadata.get("compatibility_notes")
            or candidate.get("compatibility_notes")
            or candidate.get("note"),
        }

    def _normalize_candidate(self, candidate: dict[str, Any], index: int) -> Candidate:
        metadata = dict(candidate.get("metadata") or candidate.get("metadata_json") or {})
        description = (
            metadata.get("description")
            or candidate.get("title")
            or candidate.get("description")
            or candidate.get("part_number")
            or f"candidate-{index}"
        )
        compatibility_notes = (
            metadata.get("compatibility_notes")
            or candidate.get("compatibility_notes")
            or candidate.get("compatibility_note")
            or candidate.get("note")
        )
        metadata.setdefault("description", description)
        if compatibility_notes:
            metadata["compatibility_notes"] = compatibility_notes
        if candidate.get("category") and "category" not in metadata:
            metadata["category"] = candidate.get("category")

        score = candidate.get("score")
        if score is None:
            score = candidate.get("confidence")

        return Candidate(
            id=str(candidate.get("id") or candidate.get("part_number") or f"candidate-{index}"),
            part_number=candidate.get("part_number"),
            brand=candidate.get("brand"),
            average_price_brl=candidate.get("average_price_brl") or candidate.get("price"),
            score=None if score is None else float(score),
            metadata=metadata,
        )

    def _filter_candidates(self, item: StructuredItem) -> tuple[list[Candidate], list[Candidate]]:
        accepted: list[Candidate] = []
        rejected: list[Candidate] = []

        logger.info(
            "%s item=%s query_filters=%s",
            DEBUG_PREFIX,
            item.item_id,
            _safe_json(
                {
                    "requested_item_type": item.requested_item_type,
                    "vehicle": _compact_dict(item.vehicle),
                    "raw_candidate_count": len(item.raw_candidates),
                }
            ),
        )

        if item.missing_fields:
            for index, raw_candidate in enumerate(item.raw_candidates, start=1):
                candidate = self._normalize_candidate(raw_candidate, index)
                candidate.compatibility_status = "rejected"
                candidate.reason = "insufficient_vehicle_data"
                rejected.append(candidate)
            return accepted, rejected

        for index, raw_candidate in enumerate(item.raw_candidates, start=1):
            candidate = self._normalize_candidate(raw_candidate, index)
            rejection_reason = self._candidate_rejection_reason(item=item, candidate=candidate)
            if rejection_reason is None:
                candidate.compatibility_status = "compatible"
                candidate.reason = "filtered_candidate"
                accepted.append(candidate)
            else:
                candidate.compatibility_status = "rejected"
                candidate.reason = rejection_reason
                rejected.append(candidate)

        accepted.sort(key=lambda candidate: float(candidate.score or 0.0), reverse=True)
        return accepted, rejected

    def _candidate_rejection_reason(self, *, item: StructuredItem, candidate: Candidate) -> str | None:
        metadata = candidate.metadata or {}
        candidate_text = " ".join(
            filter(
                None,
                [
                    metadata.get("category"),
                    metadata.get("description"),
                    metadata.get("compatibility_notes"),
                    candidate.brand,
                    candidate.part_number,
                ],
            )
        )
        candidate_type = infer_item_type(candidate_text)

        if item.requested_item_type == "unknown":
            return "insufficient_metadata"
        if candidate_type == "unknown":
            return "insufficient_metadata"
        if candidate_type != item.requested_item_type:
            return "wrong_category"
        if self._has_vehicle_incompatibility(item.vehicle, candidate_text):
            return "incompatible_vehicle"
        return None

    def _has_vehicle_incompatibility(self, vehicle: dict[str, Any], candidate_text: str) -> bool:
        normalized_candidate = _normalize_text(candidate_text)
        request_brand = _normalize_text(vehicle.get("brand"))
        request_model = _normalize_text(vehicle.get("model"))
        request_year = str(vehicle.get("year") or "").strip()

        if request_brand:
            mentioned_brands = [brand for brand in KNOWN_BRANDS if brand in normalized_candidate]
            if mentioned_brands and request_brand not in mentioned_brands:
                return True

        if request_model and request_model not in normalized_candidate:
            mentioned_models = [model for model in COMPATIBILITY_MODEL_HINTS if model in normalized_candidate]
            if mentioned_models and request_model not in mentioned_models:
                return True

        if request_year:
            year_ranges = _extract_year_ranges(normalized_candidate)
            if year_ranges:
                request_year_value = int(request_year)
                if not any(start <= request_year_value <= end for start, end in year_ranges):
                    return True
            else:
                mentioned_years = _extract_years(normalized_candidate)
                if mentioned_years and int(request_year) not in mentioned_years:
                    return True

        return False

    async def _rank_with_llm(
        self,
        *,
        request: RecommendationRequest,
        item: StructuredItem,
        accepted_candidates: list[Candidate],
        rejected_candidates: list[Candidate],
    ) -> tuple[list[Candidate], bool, list[str]]:
        if self._llm is None:
            return accepted_candidates, False, []

        llm_request = RecommendationRequest(
            requester_id=request.requester_id,
            vehicle=item.vehicle,
            parts=[
                PartRequest(
                    item_id=item.item_id,
                    part_number=item.part_number,
                    description=item.description,
                    quantity=item.quantity,
                    notes=item.notes,
                )
            ],
            context={
                "original_description": item.description,
                "requested_item_type": item.requested_item_type,
                "required_missing_fields": item.missing_fields,
                "prefiltered_candidates": [candidate.model_dump() for candidate in accepted_candidates],
                "rejected_candidates": [candidate.model_dump() for candidate in rejected_candidates],
            },
        )

        llm_response = await self._llm.generate(llm_request)
        accepted_map: dict[tuple[str | None, str | None], Candidate] = {}
        for candidate in accepted_candidates:
            accepted_map[(candidate.id, candidate.part_number)] = candidate

        ordered_candidates: list[Candidate] = []
        for llm_candidate in llm_response.candidates or []:
            key = (llm_candidate.id, llm_candidate.part_number)
            accepted = accepted_map.get(key)
            if accepted is None:
                accepted = next(
                    (
                        candidate
                        for candidate in accepted_candidates
                        if candidate.part_number and candidate.part_number == llm_candidate.part_number
                    ),
                    None,
                )
            if accepted is None:
                continue
            merged_metadata = {**accepted.metadata, **(llm_candidate.metadata or {})}
            accepted.metadata = merged_metadata
            accepted.score = llm_candidate.score or accepted.score
            ordered_candidates.append(accepted)

        if not ordered_candidates:
            ordered_candidates = accepted_candidates

        logger.info(
            "%s llm_accepted_input=%s llm_output=%s",
            DEBUG_PREFIX,
            _safe_json([candidate.model_dump() for candidate in accepted_candidates]),
            _safe_json([candidate.model_dump() for candidate in ordered_candidates]),
        )

        return (
            ordered_candidates,
            bool(llm_response.needs_more_info),
            list(llm_response.required_missing_fields or []),
        )

    def _summarize_item(
        self,
        item: StructuredItem,
        accepted_candidates: list[Candidate],
        rejected_candidates: list[Candidate],
    ) -> str:
        if item.missing_fields:
            return (
                f"Dados insuficientes para {CATEGORY_LABELS.get(item.requested_item_type, item.description)}; "
                f"faltam: {', '.join(item.missing_fields)}."
            )
        if accepted_candidates:
            return (
                f"{len(accepted_candidates)} candidato(s) plausíveis mantidos para "
                f"{CATEGORY_LABELS.get(item.requested_item_type, item.description)}."
            )
        if rejected_candidates:
            return "Todos os candidatos brutos foram rejeitados antes da LLM."
        return "Nenhum candidato bruto disponível para avaliação."
