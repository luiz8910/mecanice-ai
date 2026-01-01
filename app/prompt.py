from __future__ import annotations
from typing import List
from .models import ContextSource, RecommendationRequest
from .settings import settings


SYSTEM_PROMPT_PT = """Você é um assistente técnico para ajudar mecânicos a identificar peças automotivas com segurança.
Você DEVE responder exclusivamente em JSON válido seguindo o schema fornecido.
Você NÃO pode inventar códigos de peça, OEM, aplicações ou compatibilidades.
Você só pode incluir "part_numbers" quando houver evidência explícita no CONTEXTO (RAG) ou fornecida pelo usuário (foto/código).
Quando houver ambiguidade, retorne 2–5 candidatos com menor confiança e solicite confirmação via "next_question" (pergunta, foto ou medida).
Se faltarem dados críticos (ex.: eixo dianteiro/traseiro, disco/tambor), priorize a pergunta que mais reduz a ambiguidade.
Você nunca deve fornecer ou solicitar dados pessoais do proprietário do veículo.
Se não houver evidência suficiente, retorne candidates vazio ou com candidatos sem part_numbers, e peça confirmação.
"""


DEVELOPER_INSTRUCTIONS_PT = """Tarefa: identificar peça com base no input do usuário e nos trechos de referência fornecidos em CONTEXT_SOURCES.

1) Extraia o máximo de informações do veículo e peça.
2) Use SOMENTE o que estiver apoiado por evidência em CONTEXT_SOURCES ou no input do usuário.
3) Se houver mais de uma aplicação possível, crie 2–5 candidatos.
4) Gere next_question com a confirmação mínima (1 coisa) que mais separa os candidatos.
5) Retorne apenas JSON válido.
"""


SCHEMA_REMINDER_PT = """O JSON de saída DEVE seguir este shape (campos obrigatórios):
- request_id (string)
- language = "pt-BR"
- input_summary { raw_text, has_images, detected_intent="identify_part" }
- vehicle_guess { make, model, year, variant_notes, confidence(0..1), missing_fields[] }
- part_request { part_type, axle("front"|"rear"|"unknown"), symptoms_or_context }
- candidates[] (pode ser vazio)
- next_question { ask, type("question"|"photo"|"measurement"), prompt, reason }
- safety { no_owner_data=true, no_guessing_part_numbers=true, disclaimer_short }

Regras:
- part_numbers só quando houver evidência explícita no CONTEXT_SOURCES (ou código explícito do usuário).
- confidence sempre entre 0 e 1.
- Se estiver ambíguo, next_question.ask=true.
"""


def _format_context_sources(sources: List[ContextSource]) -> str:
    if not sources:
        return "CONTEXT_SOURCES:\n- (vazio)\n"

    lines = ["CONTEXT_SOURCES:"]
    for s in sources[: settings.RAG_MAX_CHUNKS_IN_PROMPT]:
        text = s.text.strip().replace("\n", " ")
        if len(text) > 900:
            text = text[:900] + "..."
        lines.append(f"- [{s.source_type}] {s.source_id}: {text}")
    return "\n".join(lines) + "\n"


def build_messages(req: RecommendationRequest) -> list[dict]:
    context_block = _format_context_sources(req.context_sources)

    user_payload = {
        "request_id": req.request_id,
        "user_text": req.user_text,
        "has_images": bool(req.images_base64),
        "known_fields": req.known_fields.model_dump(),
    }

    return [
        {"role": "system", "content": SYSTEM_PROMPT_PT},
        {"role": "developer", "content": DEVELOPER_INSTRUCTIONS_PT + "\n\n" + SCHEMA_REMINDER_PT + "\n\n" + context_block},
        {"role": "user", "content": f"INPUT_JSON:\n{user_payload}\n\nResponda apenas com JSON válido."},
    ]
