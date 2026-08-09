# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any


SYSTEM_JSON = (
    "你是资深全栈面试官与候选人教练。输出必须是合法 JSON，不要 Markdown 代码围栏，不要多余说明。"
)


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def build_generate_messages(jd: str, extra: str = "") -> list[dict[str, str]]:
    user = f"""请根据以下职位描述，生成一棵「面试题树」的根层节点（8~14 个一级题）。

每个节点包含：
- question: 面试官可能问的问题（中文）
- answer: 候选人高质量参考答案（中文，结构化、可落地，可点到 Demo/项目经验）
- tags: 字符串数组（技能标签）
- children: 先给 0~2 个二级追问（同样含 question/answer/tags/children，children 可为 []）

要求：
1. 覆盖 JD 硬性项与加分项，并单独覆盖「Vibe coding」
2. 答案要像真实面试口述：先结论，再机制，再踩坑，再与项目挂钩
3. 输出 JSON 对象：{{"title":"树标题","nodes":[...节点...]}}

职位描述：
{jd}

补充要求：
{extra or "无"}
"""
    return [
        {"role": "system", "content": SYSTEM_JSON},
        {"role": "user", "content": user},
    ]


def build_expand_messages(
    jd: str,
    path_questions: list[str],
    node_question: str,
    node_answer: str,
    count: int = 3,
) -> list[dict[str, str]]:
    trail = " → ".join(path_questions[-6:])
    user = f"""在现有面试题树上，针对「当前节点」继续向下生长 {count} 个更细的追问子节点。

职位描述（上下文）：
{jd}

祖先路径：
{trail or "(根)"}

当前问题：
{node_question}

当前答案：
{node_answer}

输出 JSON 对象：
{{
  "children": [
    {{
      "question": "...",
      "answer": "...",
      "tags": ["..."],
      "children": []
    }}
  ]
}}

要求：子题必须比当前题更深（原理/对比/排障/手写思路/结合项目），答案可直接背诵框架。
"""
    return [
        {"role": "system", "content": SYSTEM_JSON},
        {"role": "user", "content": user},
    ]


def build_sync_messages(
    jd: str,
    path_questions: list[str],
    node_question: str,
    node_answer: str,
) -> list[dict[str, str]]:
    trail = " → ".join(path_questions[-6:])
    user = f"""请根据最新岗位要求，刷新（改写增强）当前面试节点的答案，并可补充 1~2 个新的子追问。

职位描述：
{jd}

祖先路径：
{trail or "(根)"}

当前问题：
{node_question}

旧答案：
{node_answer}

输出 JSON：
{{
  "question": "可微调后的问题",
  "answer": "升级后的答案",
  "tags": ["..."],
  "new_children": [
    {{"question":"...","answer":"...","tags":["..."],"children":[]}}
  ]
}}
"""
    return [
        {"role": "system", "content": SYSTEM_JSON},
        {"role": "user", "content": user},
    ]


def parse_generate_payload(text: str) -> dict[str, Any]:
    data = _extract_json(text)
    if isinstance(data, list):
        return {"title": "面试题树", "nodes": data}
    if not isinstance(data, dict):
        raise ValueError("模型返回不是 JSON 对象")
    nodes = data.get("nodes") or data.get("children") or data.get("tree")
    if not isinstance(nodes, list):
        raise ValueError("缺少 nodes 数组")
    return {
        "title": str(data.get("title") or "面试题树"),
        "nodes": nodes,
    }


def parse_expand_payload(text: str) -> list[dict[str, Any]]:
    data = _extract_json(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        children = data.get("children") or data.get("nodes") or []
        if isinstance(children, list):
            return children
    raise ValueError("展开结果缺少 children")


def parse_sync_payload(text: str) -> dict[str, Any]:
    data = _extract_json(text)
    if not isinstance(data, dict):
        raise ValueError("同步结果不是对象")
    return data
