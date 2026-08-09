# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

from defaults import DEFAULT_BASE_URL, DEFAULT_MODEL

ProgressCb = Callable[[str], None]


class DeepSeekError(RuntimeError):
    pass


def chat(
    *,
    api_key: str,
    messages: list[dict[str, str]],
    base_url: str = DEFAULT_BASE_URL,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    timeout: int = 120,
    progress: ProgressCb | None = None,
) -> str:
    if not api_key.strip():
        raise DeepSeekError("请先填写 DeepSeek API Key")

    url = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key.strip()}",
        },
    )
    if progress:
        progress("正在请求 DeepSeek…")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise DeepSeekError(f"HTTP {e.code}: {detail[:500]}") from e
    except urllib.error.URLError as e:
        raise DeepSeekError(f"网络错误：{e}") from e

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise DeepSeekError(f"响应格式异常：{body!r}"[:500]) from e
    if progress:
        progress("DeepSeek 返回完成")
    return str(content or "")


def test_connection(api_key: str, base_url: str, model: str) -> str:
    return chat(
        api_key=api_key,
        base_url=base_url,
        model=model,
        messages=[
            {"role": "system", "content": "只回复 OK"},
            {"role": "user", "content": "ping"},
        ],
        temperature=0,
        timeout=30,
    )
