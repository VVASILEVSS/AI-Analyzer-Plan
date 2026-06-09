"""
AI Analyzer v2.1 — LLM Service
Sends market data to local LLM (LM Studio / OpenAI compatible) and parses signal.
"""

import json
import logging
from typing import Optional

import httpx

from app.core.config import OLLAMA_URL, LLM_MODEL, LLM_TIMEOUT, logger

SYSTEM_PROMPT = """Ты — профессиональный аналитик криптовалютных рынков. 
Анализируй предоставленные рыночные данные и верни JSON-сигнал.

Формат ответа — ТОЛЬКО валидный JSON без markdown, без комментариев:

{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "regime": "TREND_UP" | "TREND_DOWN" | "RANGE" | "VOLATILE",
  "reasons": ["причина 1", "причина 2"],
  "risks": ["риск 1", "риск 2"]
}

Правила:
- signal: основная рекомендация (BUY/SELL/HOLD)
- confidence: уверенность 0-100%
- regime: текущий режим рынка
- reasons: 2-4 аргумента ЗА сигнал (на русском)
- risks: 1-3 предупреждения (на русском)
- Отвечай ТОЛЬКО JSON, ничего больше
"""


class LLMService:
    """Async wrapper for OpenAI-compatible API (LM Studio / Ollama)."""

    def __init__(self):
        self.base_url = OLLAMA_URL
        self.model = LLM_MODEL
        self.timeout = LLM_TIMEOUT

    async def generate_signal(self, market_data: str) -> Optional[dict]:
        prompt = f"Рыночные данные:\n{market_data}\n\nПроанализируй и выдай JSON-сигнал."

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Try OpenAI-compatible format (LM Studio)
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 512,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()

                result = response.json()
                text = result["choices"][0]["message"]["content"].strip()

                if not text:
                    logger.warning("LLM returned empty response")
                    return None

                # Clean markdown code blocks if present
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    text = text.strip()

                signal = json.loads(text)
                logger.info(f"LLM signal: {signal.get('signal')} @ {signal.get('confidence')}%")
                return signal

        except KeyError as e:
            logger.error(f"Unexpected LLM response format: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"LLM connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM unexpected error: {e}")
            return None


llm_service = LLMService()