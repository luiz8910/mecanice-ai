

class LllAdapter:
    
    def __init__(self):
        pass

    async def call_openai(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        force_json: bool = True,
    ) -> str:
        """
        Adapter para OpenAI "oficial".
        Neste projeto, ele pode reutilizar o mesmo caminho do openai_compatible,
        porque os endpoints e formato são iguais.
        """
        if not settings.LLM_API_KEY:
            raise LLMError("LLM_API_KEY não configurada.")

        # Aqui, usamos LLM_BASE_URL por padrão (já aponta para api.openai.com/v1).
        base = settings.LLM_BASE_URL.rstrip("/")
        url = f"{base}/chat/completions"

        payload: dict[str, Any] = {
            "model": model or settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if force_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }

        data = await _post_json(
            url=url,
            headers=headers,
            payload=payload,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )
        return _get_first_choice_content(data)