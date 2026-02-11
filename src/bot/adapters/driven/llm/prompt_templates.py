"""Prompt templates for the OpenAI-compatible LLM calls.

These templates are specific to the *adapter* layer — they know about the
wire format expected by the LLM provider (chat-completion messages list)
but carry no domain logic.
"""

from __future__ import annotations

from typing import List

from src.bot.application.dtos.recommendation.recommendation_request import (
    RecommendationRequest,
)
from src.bot.application.dtos.recommendation.part_request import PartRequest


# ── System prompt (pt-BR) ────────────────────────────────────────────

SYSTEM_PROMPT = """\
Você é um assistente técnico especializado em identificar peças automotivas para mecânicos.
Você DEVE responder exclusivamente em JSON válido seguindo o schema fornecido.
Seu objetivo é retornar o part_number (código único da peça/OEM/aftermarket) de cada candidato.
Sempre que possível, retorne candidatos de MARCAS DIFERENTES para dar variedade ao mecânico.
Incluir pelo menos a marca original (OEM) e 2-3 marcas aftermarket de qualidade conhecida.
Cada candidato DEVE ter um part_number real e verificável — nunca invente códigos.
"""

# ── Developer / instruction block ────────────────────────────────────

DEVELOPER_INSTRUCTIONS = """\
Tarefa: analisar o pedido do mecânico e retornar peças com part_number único para que
o vendedor da autopeça consiga localizar a peça exata no sistema dele.

Regras:
1. Extraia informações do veículo e da peça solicitada.
2. Retorne de 3 a 5 candidatos de MARCAS DIFERENTES (OEM + aftermarket).
3. Cada candidato DEVE ter:
   - part_number: código único real da peça (ex: "SYL-1382", "TRW GDB1550", "96534653")
   - brand: nome da marca/fabricante (ex: "Fras-le", "TRW", "Bosch", "Cobreq")
   - average_price_brl: preço médio estimado em reais (float). Baseie-se em valores de mercado conhecidos.
   - description: descrição curta da peça
   - compatibility_notes: notas de compatibilidade com o veículo informado
  - fitment_keys: lista de chaves de confirmação (ex: "dianteiro/traseiro", "com/sem ABS", "com/sem sensor", "motor", "ano")
  - warning_flags: lista curta de alertas/riscos de confusão (ex: "varia por motor", "há versões com sensor")
  - required_questions: 1 a 3 perguntas objetivas para desambiguar quando houver incerteza
4. score (float 0..1) indica confiança de que aquele part_number é compatível.
5. Se houver ambiguidade (ex: dianteiro vs traseiro), retorne candidatos com score menor
  e preencha "required_questions".
6. Retorne APENAS JSON válido.

Schema de saída:
{
  "id": "<echo do requester_id>",
  "candidates": [
    {
      "id": "<identificador interno>",
      "part_number": "<código único da peça>",
      "brand": "<marca/fabricante>",
      "average_price_brl": <float preço médio em R$>,
      "score": <float 0..1>,
      "metadata": {
        "description": "...",
        "compatibility_notes": "...",
        "origin": "OEM" | "aftermarket",
        "fitment_keys": ["..."],
        "warning_flags": ["..."],
        "required_questions": ["..."]
      }
    }
  ],
  "evidences": [
    {
      "id": "<source>",
      "score": <float 0..1>,
      "text": "<trecho de referência>"
    }
  ],
  "raw": {}
}

Exemplo de resposta para "pastilha de freio dianteira Vectra 2.2 2000":
{
  "id": "mec_001",
  "candidates": [
    {"id": "1", "part_number": "96534653", "brand": "GM (OEM)", "average_price_brl": 189.90, "score": 0.95, "metadata": {"description": "Pastilha freio dianteira original", "compatibility_notes": "Vectra 2.0/2.2 1997-2005", "origin": "OEM", "fitment_keys": ["eixo (dianteiro/traseiro)", "com/sem ABS", "ano"], "warning_flags": ["pode variar por versão com/sem ABS"], "required_questions": []}},
    {"id": "2", "part_number": "SYL-1382", "brand": "Fras-le", "average_price_brl": 119.90, "score": 0.90, "metadata": {"description": "Pastilha freio dianteira", "compatibility_notes": "Vectra todos 1997-2005", "origin": "aftermarket", "fitment_keys": ["eixo (dianteiro/traseiro)", "com/sem ABS", "ano"], "warning_flags": ["pode variar por versão com/sem ABS"], "required_questions": []}},
    {"id": "3", "part_number": "GDB1550", "brand": "TRW", "average_price_brl": 139.90, "score": 0.90, "metadata": {"description": "Pastilha freio dianteira", "compatibility_notes": "Vectra 2.0/2.2 8v/16v", "origin": "aftermarket", "fitment_keys": ["eixo (dianteiro/traseiro)", "com/sem ABS", "ano"], "warning_flags": ["pode variar por versão com/sem ABS"], "required_questions": []}}
  ],
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


def build_messages(request: RecommendationRequest) -> list[dict[str, str]]:
    """Build the chat-completion messages list from a RecommendationRequest."""

    vehicle_block = _format_vehicle(request.vehicle)
    parts_block = _format_parts(request.parts)
    context_block = ""
    if request.context:
        context_block = f"\nContexto adicional: {request.context}"

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
