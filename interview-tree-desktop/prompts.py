# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any


SYSTEM_JSON = (
    "你是资深全栈面试官与候选人教练。输出必须是合法 JSON 对象，不要 Markdown 代码围栏，不要多余说明。"
)


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise ValueError("模型返回为空")
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    candidates: list[str] = [text]
    start_obj, end_obj = text.find("{"), text.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        candidates.append(text[start_obj : end_obj + 1])
    start_arr, end_arr = text.find("["), text.rfind("]")
    if start_arr >= 0 and end_arr > start_arr:
        candidates.append(text[start_arr : end_arr + 1])

    last_err: Exception | None = None
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError as e:
            last_err = e
            # trailing comma / truncated trailing garbage
            repaired = re.sub(r",\s*([}\]])", r"\1", cand)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e2:
                last_err = e2

    snippet = text[:240].replace("\n", " ")
    raise ValueError(
        f"无法解析模型 JSON（常见于输出被截断）。请再点一次刷新。"
        f" 细节：{last_err}; 片段：{snippet}"
    )


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


def build_refresh_messages(
    jd: str, existing_outline: str, extra: str = ""
) -> list[dict[str, str]]:
    # Keep prompt small to reduce truncation / context overflow failures.
    jd_short = (jd or "").strip()
    if len(jd_short) > 1800:
        jd_short = jd_short[:1800] + "\n…(JD 已截断)"
    user = f"""请在「保留并增强现有面试题树」的前提下做一次小批量刷新。

硬性规则：
1. 禁止删除、替换、清空任何已有题目；只能追加新题，或补充已有题的答案/子追问
2. 本次必须控制体量：updates 最多 4 条，new_nodes 最多 3 条；每条 answer_supplement 不超过 120 字
3. new_children 每个 update 最多 2 个，答案各不超过 80 字
4. match_question 必须尽量贴合大纲里已有题干
5. 只输出一个 JSON 对象，字段齐全但内容精简，确保完整可解析

输出 JSON：
{{
  "title": "可选",
  "updates": [
    {{
      "match_question": "与现有某题相近的题干",
      "answer_supplement": "增量补充（可空字符串）",
      "tags_add": ["标签"],
      "new_children": [
        {{"question":"...","answer":"...","tags":["..."],"children":[]}}
      ]
    }}
  ],
  "new_nodes": [
    {{"question":"...","answer":"...","tags":["..."],"children":[]}}
  ]
}}

职位描述：
{jd_short}

现有题树大纲（勿删除）：
{existing_outline or "(空树)"}

补充要求：
{extra or "优先补 JD 缺口与薄弱答案"}
"""
    return [
        {"role": "system", "content": SYSTEM_JSON},
        {"role": "user", "content": user},
    ]


def parse_refresh_payload(text: str) -> dict[str, Any]:
    data = _extract_json(text)
    if isinstance(data, list):
        # model sometimes returns bare node list
        return {"title": None, "updates": [], "new_nodes": data}
    if not isinstance(data, dict):
        raise ValueError("刷新结果不是 JSON 对象")
    updates = data.get("updates")
    new_nodes = data.get("new_nodes") or data.get("nodes") or data.get("children")
    return {
        "title": data.get("title"),
        "updates": updates if isinstance(updates, list) else [],
        "new_nodes": new_nodes if isinstance(new_nodes, list) else [],
    }


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


def build_coding_messages(jd: str, extra: str = "", count: int = 3) -> list[dict[str, str]]:
    jd_short = (jd or "").strip()
    if len(jd_short) > 1600:
        jd_short = jd_short[:1600] + "\n…(JD 已截断)"
    user = f"""请根据职位描述生成 {count} 道「可本地手写」的面试实操编程题（Python）。

硬性要求：
1. 每题必须能在单文件 Python 里完成，15~30 分钟难度
2. 紧扣 JD（Nest/Next/SQL/RBAC/上传/流媒体/Linux 运维相关算法或小函数均可）
3. starter_code 给出函数签名与 TODO；solution_code 给出完整可运行参考实现
4. tests 为 3~5 条可直接 exec 的断言或短代码（字符串），不要依赖第三方库
5. 只输出 JSON 对象

输出：
{{
  "nodes": [
    {{
      "kind": "coding",
      "question": "【实操】题目标题",
      "answer": "考点说明与口述提示（中文）",
      "tags": ["实操", "..."],
      "language": "python",
      "starter_code": "def foo(...):\\n    pass\\n",
      "solution_code": "def foo(...):\\n    ...\\n",
      "tests": ["assert foo(...) == ...", "..."],
      "hint": "一句提示",
      "children": []
    }}
  ]
}}

职位描述：
{jd_short}

补充要求：
{extra or "覆盖鉴权、数据结构、字符串/数组、并发安全中的至少一类"}
"""
    return [
        {"role": "system", "content": SYSTEM_JSON},
        {"role": "user", "content": user},
    ]


def parse_coding_payload(text: str) -> list[dict[str, Any]]:
    data = _extract_json(text)
    if isinstance(data, list):
        nodes = data
    elif isinstance(data, dict):
        nodes = data.get("nodes") or data.get("exercises") or data.get("children") or []
    else:
        raise ValueError("实操题结果不是 JSON")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("缺少实操题 nodes")
    out: list[dict[str, Any]] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        n = {**n, "kind": "coding"}
        out.append(n)
    if not out:
        raise ValueError("没有有效的实操题")
    return out
