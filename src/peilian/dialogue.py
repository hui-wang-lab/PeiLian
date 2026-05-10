from __future__ import annotations

import re
from typing import Any

from openai import OpenAI

from .config import Settings
from .persona import Persona
from .prompts import render_customer_system_prompt
from .scenario import Scenario


_LEADING_STAGE_DIRECTION_RE = re.compile(r"^\s*(?:[（(][^（）()\n]{1,80}[）)]\s*)+")


def strip_stage_directions(text: str) -> str:
    """去掉回复开头的动作/神态舞台提示，保留真正说出口的话。"""
    return _LEADING_STAGE_DIRECTION_RE.sub("", text).strip()


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
        *,
        persona_meta: Any = None,
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
        self._persona = persona
        self._scenario = scenario
        self._persona_meta = persona_meta

        # P4: CustomerState 初始化（仅当传入 persona_meta）
        if persona_meta is not None:
            from .customer_state import CustomerState
            self._customer_state: CustomerState | None = CustomerState.initial(
                persona, persona_meta
            )
        else:
            self._customer_state = None

        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._render_system_prompt()}
        ]

    def _render_system_prompt(self) -> str:
        """每轮调用前重新渲染，注入 state_summary（P4）。"""
        summary = ""
        if self._customer_state is not None and self._persona_meta is not None:
            from .state_summary import render_state_summary
            summary = render_state_summary(
                self._customer_state, self._persona, self._persona_meta
            )
        return render_customer_system_prompt(
            self._persona, self._scenario, state_summary=summary
        )

    def send_user(self, text: str) -> str:
        # P4: 每轮调用前刷新 system prompt
        self.messages[0] = {"role": "system", "content": self._render_system_prompt()}

        self.messages.append({"role": "user", "content": text})
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self.messages,
            temperature=0.7,
        )
        answer = strip_stage_directions(response.choices[0].message.content or "")
        self.messages.append({"role": "assistant", "content": answer})

        # P4: 生成后更新 CustomerState 并同步 messages[0]
        if self._customer_state is not None and self._persona_meta is not None:
            from .customer_state import update_state
            self._customer_state = update_state(
                self._customer_state,
                text,
                answer,
                persona=self._persona,
                persona_meta=self._persona_meta,
            )
            self.messages[0] = {
                "role": "system",
                "content": self._render_system_prompt(),
            }

        return answer

    def reset(self) -> None:
        # P4: 同步重置 customer_state
        if self._persona_meta is not None:
            from .customer_state import CustomerState
            self._customer_state = CustomerState.initial(
                self._persona, self._persona_meta
            )
        self.messages = [{"role": "system", "content": self._render_system_prompt()}]

    @property
    def customer_state(self) -> Any | None:
        """P4: 只读属性，返回当前 CustomerState。"""
        return self._customer_state
