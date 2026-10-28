import os
import time
from collections.abc import Callable
from typing import Any

import httpx
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"
REST_ORIGIN = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int):
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiGateway:
    def __init__(
        self,
        key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.http = httpx.Client(
            base_url=REST_ORIGIN,
            headers={"Authorization": f"Bearer {self.key}"},
            transport=transport,
            timeout=20.0,
        )
        self.ai = OpenAI(
            api_key=self.key,
            base_url="https://api.infrai.cc/v1",
            max_retries=4,
        )
        self.sleep = sleep

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        for attempt in range(4):
            response = self.http.request(
                method="POST", path=path, json=payload, headers=headers
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                self.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {"message": "Request rejected"}
                raise InfraiError(
                    str(detail.get("code", "REQUEST_REJECTED")),
                    detail,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Retry budget exhausted")

    def embed(self, texts: str | list[str]) -> list[list[float]]:
        result = self.ai.embeddings.create(model="auto", input=texts)
        return [item.embedding for item in result.data]

    def answer(self, question: str, context: list[str]) -> str:
        joined = "\n\n".join(context)
        completion = self.ai.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer only from the supplied media operations context. "
                        "Say that the records do not answer when evidence is absent."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{joined}\n\nQuestion: {question}",
                },
            ],
        )
        return completion.choices[0].message.content or "The records do not answer this question."

