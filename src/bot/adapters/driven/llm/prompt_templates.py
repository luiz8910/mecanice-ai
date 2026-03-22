"""Prompt templates for the OpenAI-compatible LLM calls.

These templates are specific to the *adapter* layer — they know about the
wire format expected by the LLM provider (chat-completion messages list)
but carry no domain logic.
"""

from __future__ import annotations

import json
from typing import List

from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest


# ── System prompt (pt-BR) ────────────────────────────────────────────

SYSTEM_PROMPT = """\
Você é um assistente técnico especializado em organizar recomendações de peças automotivas.
Você DEVE responder exclusivamente em JSON válido seguindo o schema fornecido.
Você NUNCA pode inventar candidatos, códigos, marcas ou compatibilidades fora da lista de candidatos pré-filtrados recebida.
"""

# ── Developer / instruction block ────────────────────────────────────

DEVELOPER_INSTRUCTIONS = """\
Tarefa: analisar o pedido do mecânico e organizar somente os candidatos pré-filtrados pelo backend.

Regras:
1. Use o veículo estruturado recebido como verdade principal.
2. Você só pode reordenar, resumir e explicar os candidatos já pré-filtrados.
3. Nunca adicione candidatos novos.
4. Se faltarem dados, responda com "needs_more_info": true, preencha "required_missing_fields" e mantenha "candidates": [].
5. Se houver candidatos plausíveis, retorne somente candidatos vindos da lista pré-filtrada.
6. Preserve os ids/part_numbers recebidos.
7. Retorne APENAS JSON válido.

Schema de saída:
{
  "id": "<echo do requester_id>",
  "requested_item_type": "<tipo normalizado>",
  "needs_more_info": false,
  "required_missing_fields": [],
  "candidates": [],
  "evidences": [
    {
      "id": "<source>",
      "score": <float 0..1>,
      "text": "<trecho de referência>"
    }
  ],
  "raw": {}
}

Exemplo de resposta quando existem candidatos plausíveis:
{
  "id": "mec_001",
  "requested_item_type": "spark_plug",
  "needs_more_info": false,
  "required_missing_fields": [],
  "candidates": [
    {"id": "cand-1", "part_number": "BKR6E-11", "brand": "NGK", "average_price_brl": 29.9, "score": 0.92, "compatibility_status": "compatible", "reason": "best_match", "metadata": {"description": "Vela de ignição", "compatibility_notes": "Palio 1.0 2012-2016", "ranking_reason": "Melhor aderência ao veículo informado."}}
  ],
  "evidences": [],
  "raw": {}
}

Exemplo quando faltam dados:
{
  "id": "mec_001",
  "requested_item_type": "alternator",
  "needs_more_info": true,
  "required_missing_fields": ["engine", "version"],
  "candidates": [],
  "evidences": [],
  "raw": {}
}
"""


def _format_parts(parts: List[PartRequest] | None) -> str:
    if not parts:
        return "Nenhuma peça especificada."
    lines: list[str] = []
    for p in parts:
        desc = p.description or "sem descrição"
        pn = p.part_number or "sem código"
        lines.append(f"- {desc} (código: {pn}, qtd: {p.quantity})")
    return "\n".join(lines)


def _format_vehicle(vehicle: dict | None) -> str:
    if not vehicle:
        return "Veículo não informado."
    parts = [f"{k}: {v}" for k, v in vehicle.items() if v]
    return ", ".join(parts) if parts else "Veículo não informado."


def _format_prefiltered_candidates(context: dict | None) -> str:
    if not context:
        return "[]"
    candidates = context.get("prefiltered_candidates") or []
    return json.dumps(candidates, ensure_ascii=False)


def build_messages(request: RecommendationRequest) -> list[dict[str, str]]:
    """Build the chat-completion messages list from a RecommendationRequest."""

    vehicle_block = _format_vehicle(request.vehicle)
    parts_block = _format_parts(request.parts)
    context_block = ""
    if request.context:
        context_block = (
            f"\nContexto adicional: {json.dumps(request.context, ensure_ascii=False)}"
            f"\nCandidatos pré-filtrados: {_format_prefiltered_candidates(request.context)}"
        )

    user_content = (
        f"Solicitante: {request.requester_id or 'anônimo'}\n"
        f"Veículo: {vehicle_block}\n"
        f"Peças solicitadas:\n{parts_block}"
        f"{context_block}\n\n"
        "Responda APENAS com JSON válido."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "developer", "content": DEVELOPER_INSTRUCTIONS},
        {"role": "user", "content": user_content},
    ]
