"""MiniMax M2.7 LLM API 客户端。

兼容 OpenAI Chat Completions 格式，支持文本和图片输入。
使用 httpx 作为 HTTP 客户端，支持指数退避重试。
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import httpx
from PIL import Image

from ..config.schema import LLMConfig
from ..utils.exceptions import LLMApiError, LLMRateLimitError, LLMTimeoutError
from ..utils.logger import setup_logger


@dataclass
class LLMMessage:
    role: str      # "system" | "user" | "assistant"
    content: str
    images: Optional[List[Image.Image]] = None  # 多模态图片（可选）


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类，便于切换不同模型供应商。"""

    @abstractmethod
    def chat(self, messages: List[LLMMessage]) -> str:
        ...

    @abstractmethod
    def chat_with_image(self, messages: List[LLMMessage], image: Image.Image) -> str:
        ...


class MiniMaxClient(BaseLLMClient):
    """MiniMax M2.7 API 客户端。

    MiniMax 兼容 OpenAI Chat Completions 格式:
        POST https://api.minimax.chat/v1/chat/completions
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._logger = setup_logger()

    def chat(self, messages: List[LLMMessage]) -> str:
        """发送纯文本对话请求。

        Args:
            messages: 对话消息列表。

        Returns:
            LLM 回复的文本内容。

        Raises:
            LLMApiError: API 返回错误。
            LLMTimeoutError: 请求超时。
            LLMRateLimitError: 触发限流。
        """
        payload = {
            "model": self._config.model,
            "messages": self._build_request_messages(messages),
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_output_tokens,
        }
        return self._call_api(payload)

    def chat_with_image(self, messages: List[LLMMessage], image: Image.Image) -> str:
        """发送带图片的多模态对话请求。

        Args:
            messages: 对话消息列表。
            image: 要发送的图片。

        Returns:
            LLM 回复的文本内容。
        """
        payload = {
            "model": self._config.model,
            "messages": self._build_request_messages(messages, image),
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_output_tokens,
        }
        return self._call_api(payload)

    def _call_api(self, payload: dict) -> str:
        """核心 HTTP 请求，带指数退避重试。

        Raises:
            LLMTimeoutError: 全部重试后仍超时。
            LLMApiError: API 返回非 200 状态码。
            LLMRateLimitError: 触发限流。
        """
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(self._config.max_retries + 1):
            try:
                with httpx.Client(timeout=self._config.timeout) as client:
                    response = client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    return self._parse_response(response.json())

                elif response.status_code == 429:
                    self._logger.warning("LLM rate limited, attempt %d", attempt + 1)
                    last_error = LLMRateLimitError(f"API 限流 (HTTP {response.status_code})")
                elif response.status_code >= 500:
                    self._logger.warning("LLM server error %d, attempt %d", response.status_code, attempt + 1)
                    last_error = LLMApiError(f"API 服务器错误 (HTTP {response.status_code}): {response.text[:200]}")
                else:
                    last_error = LLMApiError(f"API 错误 (HTTP {response.status_code}): {response.text[:200]}")
                    break  # 非 5xx / 429，不重试

            except httpx.TimeoutException as e:
                self._logger.warning("LLM timeout, attempt %d", attempt + 1)
                last_error = LLMTimeoutError(f"请求超时 ({self._config.timeout}s)")
            except httpx.RequestError as e:
                self._logger.error("LLM request failed: %s", e)
                last_error = LLMApiError(f"网络错误: {e}")

            if attempt < self._config.max_retries:
                delay = 2 ** attempt  # 1s, 2s, 4s...
                self._logger.info("Retrying in %ds...", delay)
                time.sleep(delay)

        if last_error:
            raise last_error
        raise LLMApiError("未知错误")

    def _build_request_messages(self, messages: List[LLMMessage], image: Optional[Image.Image] = None) -> list:
        """将内部消息格式转为 OpenAI 兼容的 API 请求格式。"""
        api_messages = []

        for msg in messages:
            if msg.images or image:
                # 多模态消息
                content_parts = []

                # 文本部分
                if msg.content:
                    content_parts.append({"type": "text", "text": msg.content})

                # 图片部分（优先传参图片，其次消息自带图片）
                imgs: List[Image.Image] = []
                if image:
                    imgs.append(image)
                if msg.images:
                    imgs.extend(msg.images)

                for img in imgs:
                    import base64
                    import io
                    buf = io.BytesIO()
                    # 压缩大图以减少传输
                    img.save(buf, format="JPEG", quality=85)
                    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    })

                api_messages.append({"role": msg.role, "content": content_parts})

            else:
                # 纯文本消息
                api_messages.append({"role": msg.role, "content": msg.content})

        return api_messages

    def _parse_response(self, response: dict) -> str:
        """从 API 响应中提取回复文本。"""
        return response["choices"][0]["message"]["content"]
