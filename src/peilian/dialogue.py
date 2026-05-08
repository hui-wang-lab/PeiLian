from __future__ import annotations

from typing import Any

from openai import OpenAI

from .config import Settings
from .persona import Persona
from .prompts import render_customer_system_prompt
from .scenario import Scenario


class Dialogue:
    """最小多轮对话引擎。

    维护一份完整 messages 历史，每次 send_user 一次 LLM 调用拿响应。
    不流式、不异步、不裁剪上下文。
    """

    def __init__(
        self,
        persona: Persona,
        scenario: Scenario,
        settings: Settings,
    ) -> None:
        if not settings.api_key:
            raise RuntimeError(
                "未检测到 OPENAI_API_KEY；请在 .env 中配置后重试。"
            )
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )
        self._model = settings.model or "gpt-4o-mini"
        self._system_prompt = render_customer_system_prompt(persona, scenario)
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt}
        ]
        # P2: observer hooks can be added around message handling later.

    def send_user(self, text: str) -> str:
        self.messages.append({"role": "user", "content": text})
        # P2: pre-message observer hook would go here.
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self.messages,
            temperature=0.7,
        )
        answer = response.choices[0].message.content or ""
        self.messages.append({"role": "assistant", "content": answer})
        # P2: post-message observer hook would go here.
        return answer

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": self._system_prompt}]
