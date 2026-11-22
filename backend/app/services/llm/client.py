"""Gemini API client with JSON output, retries and clear error messages.

All LLM access goes through `get_llm()`, so tests can swap in a fake and another
provider could be added without touching the RAG pipeline.
"""

import json
import logging
import threading
import time
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """The LLM call failed. The message is safe to show to the user."""


class LLMNotConfigured(LLMError):
    pass


class ImageInput(BaseModel):
    data: bytes
    mime_type: str = "image/png"


class LLMClient(Protocol):
    def generate_json(
        self,
        system: str,
        prompt: str,
        schema: type[BaseModel],
        images: list[ImageInput] | None = None,
        temperature: float | None = None,
    ) -> BaseModel: ...


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_json(
        self,
        system: str,
        prompt: str,
        schema: type[BaseModel],
        images: list[ImageInput] | None = None,
        temperature: float | None = None,
    ) -> BaseModel:
        from google.genai import errors, types

        contents: list[Any] = [types.Part.from_bytes(data=img.data, mime_type=img.mime_type) for img in images or []]
        contents.append(prompt)
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=settings.GEMINI_TEMPERATURE if temperature is None else temperature,
            # Constrained decoding: the model can only produce JSON matching this schema.
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )

        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
                return schema.model_validate(json.loads(response.text or "{}"))
            except errors.ClientError as exc:
                if exc.code == 429 and attempt < settings.LLM_MAX_RETRIES:
                    wait = 2 ** (attempt + 2)  # 4 s, 8 s: free-tier limits are per minute
                    logger.warning("Gemini rate limit hit; retrying in %ss", wait)
                    time.sleep(wait)
                    continue
                if exc.code == 429:
                    raise LLMError("The AI service is busy (rate limit reached). Please wait a minute and try again.") from exc
                if exc.code in (401, 403):
                    raise LLMError("The Gemini API key is invalid or lacks permission.") from exc
                if exc.code == 404:
                    raise LLMError(f"Gemini model '{self.model}' was not found. Check GEMINI_MODEL in .env.") from exc
                raise LLMError(f"The AI service rejected the request ({exc.code}).") from exc
            except errors.ServerError as exc:
                if attempt < settings.LLM_MAX_RETRIES:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise LLMError("The AI service is temporarily unavailable. Please try again.") from exc
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt < settings.LLM_MAX_RETRIES:
                    continue
                raise LLMError("The AI service returned an unexpected response.") from exc
        raise LLMError("The AI service could not be reached.")


_client: LLMClient | None = None
_lock = threading.Lock()


def get_llm() -> LLMClient:
    global _client
    if not settings.GEMINI_API_KEY:
        raise LLMNotConfigured(
            "No Gemini API key is configured. Add GEMINI_API_KEY to backend/.env (free key: https://aistudio.google.com/apikey)."
        )
    with _lock:
        if _client is None:
            _client = GeminiClient(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        return _client
