"""Tests for Ollama Service."""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.ollama_service import OllamaService


@pytest.fixture
def ollama():
    return OllamaService(base_url="http://localhost:11434")


class TestOllamaService:
    def test_initialization(self, ollama):
        assert ollama.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama):
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("app.services.ollama_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await ollama.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama):
        from httpx import ConnectError

        with patch("app.services.ollama_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=ConnectError("Connection refused")
            )
            result = await ollama.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_success(self, ollama):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"signal": "BUY", "confidence": 0.8}',
            "eval_count": 100,
            "eval_duration": 5000000000,
        }

        with patch("app.services.ollama_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await ollama.generate(prompt="Analyze BTC/USDT")
            assert result["success"] is True
            assert result["response"] == '{"signal": "BUY", "confidence": 0.8}'

    @pytest.mark.asyncio
    async def test_generate_timeout(self, ollama):
        from httpx import TimeoutException

        with patch("app.services.ollama_service.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=TimeoutException("Timeout")
            )
            result = await ollama.generate(prompt="test")
            assert result["success"] is False
            assert result["error"] == "Timeout"
