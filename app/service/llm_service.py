from typing import Any
import json
from app.dtos.recommendation_response import RecommendationResponse
from app.settings import settings

class LllService:

    def __init__(self):
        pass

    async def generate_recommendation(self, messages: list[dict[str, Any]]) -> RecommendationResponse:
        """
        Recebe messages já preparados (podem conter imagem).
        Chama o provider configurado e valida no schema RecommendationResponse.
        """
        provider = (settings.LLM_PROVIDER or "openai_compatible").strip()

        if provider == "openai":
            raw = await call_openai(messages, force_json=True)
        elif provider == "openai_compatible":
            raw = await call_openai_compatible(messages, force_json=True)
        else:
            raise LLMError(f"Provider LLM não suportado: {provider}")

        # Se response_format funcionou, raw já deve ser JSON puro.
        # Mesmo assim, deixo fallback para não quebrar caso o provedor retorne texto.
        raw = raw.strip()
        json_text = raw
        if not raw.startswith("{"):
            json_text = _extract_json(raw)

        try:
            obj: Any = json.loads(json_text)
        except Exception as e:
            raise LLMError(f"JSON inválido retornado pelo modelo: {e} - raw={raw[:500]}")

        try:
            return RecommendationResponse.model_validate(obj)
        except Exception as e:
        raise LLMError(f"Resposta não bate no schema: {e}")