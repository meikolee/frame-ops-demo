# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str = "n") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def app_dir() -> Path:
    # PyInstaller onefile: prefer directory of the executable
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    d = app_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return data_dir() / "config.json"


def tree_path() -> Path:
    return data_dir() / "interview_tree.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {
            "api_key": "",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "jd_text": "",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(cfg: dict[str, Any]) -> None:
    config_path().write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def empty_tree(title: str = "面试题树") -> dict[str, Any]:
    return {
        "version": 1,
        "title": title,
        "updated_at": utc_now(),
        "nodes": [],
    }


def normalize_node(raw: dict[str, Any]) -> dict[str, Any]:
    children_raw = raw.get("children") or []
    children = [
        normalize_node(c) for c in children_raw if isinstance(c, dict)
    ]
    return {
        "id": str(raw.get("id") or new_id()),
        "question": str(raw.get("question") or "").strip() or "（未命名问题）",
        "answer": str(raw.get("answer") or "").strip(),
        "tags": [str(t) for t in (raw.get("tags") or [])],
        "children": children,
        "updated_at": str(raw.get("updated_at") or utc_now()),
        "source": str(raw.get("source") or "deepseek"),
    }


def normalize_tree(raw: dict[str, Any]) -> dict[str, Any]:
    nodes = [normalize_node(n) for n in (raw.get("nodes") or []) if isinstance(n, dict)]
    return {
        "version": int(raw.get("version") or 1),
        "title": str(raw.get("title") or "面试题树"),
        "updated_at": str(raw.get("updated_at") or utc_now()),
        "nodes": nodes,
    }


def load_tree() -> dict[str, Any]:
    path = tree_path()
    if not path.exists():
        return empty_tree()
    return normalize_tree(json.loads(path.read_text(encoding="utf-8")))


def save_tree(tree: dict[str, Any]) -> None:
    tree = normalize_tree(tree)
    tree["updated_at"] = utc_now()
    tree_path().write_text(
        json.dumps(tree, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_node(
    nodes: list[dict[str, Any]], node_id: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None, int]:
    for i, n in enumerate(nodes):
        if n["id"] == node_id:
            return n, nodes, i
        found, parent, idx = find_node(n.get("children") or [], node_id)
        if found is not None:
            return found, parent, idx
    return None, None, -1


def path_to_node(
    nodes: list[dict[str, Any]], node_id: str, trail: list[str] | None = None
) -> list[str] | None:
    trail = list(trail or [])
    for n in nodes:
        cur = trail + [n["question"]]
        if n["id"] == node_id:
            return cur
        hit = path_to_node(n.get("children") or [], node_id, cur)
        if hit is not None:
            return hit
    return None


def walk(nodes: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for n in nodes:
        yield n
        yield from walk(n.get("children") or [])


def attach_children(node: dict[str, Any], children: list[dict[str, Any]]) -> None:
    existing = node.setdefault("children", [])
    for c in children:
        existing.append(normalize_node({**c, "source": c.get("source") or "deepseek"}))
    node["updated_at"] = utc_now()


def replace_node_content(node: dict[str, Any], patch: dict[str, Any]) -> None:
    if patch.get("question"):
        node["question"] = str(patch["question"]).strip()
    if patch.get("answer") is not None:
        node["answer"] = str(patch["answer"]).strip()
    if patch.get("tags") is not None:
        node["tags"] = [str(t) for t in patch["tags"]]
    node["updated_at"] = utc_now()
    node["source"] = "deepseek-sync"
    new_children = patch.get("new_children") or patch.get("children") or []
    if isinstance(new_children, list) and new_children:
        attach_children(node, new_children)


def export_markdown(tree: dict[str, Any]) -> str:
    lines = [f"# {tree.get('title') or '面试题树'}", ""]

    def render(nodes: list[dict[str, Any]], depth: int) -> None:
        for n in nodes:
            prefix = "#" * min(depth + 2, 6)
            tags = ", ".join(n.get("tags") or [])
            lines.append(f"{prefix} {n['question']}")
            if tags:
                lines.append(f"*标签：{tags}*")
            lines.append("")
            lines.append(n.get("answer") or "（暂无答案）")
            lines.append("")
            render(n.get("children") or [], depth + 1)

    render(tree.get("nodes") or [], 0)
    return "\n".join(lines)


def seed_offline_tree(jd: str) -> dict[str, Any]:
    """No-network fallback so EXE remains usable offline."""
    topics = [
        (
            "请介绍你完整交付并维护过的 Node.js + React 线上系统",
            "先交代业务与规模，再讲技术选型、发布与值班、一次线上事故复盘。可挂 FRAME Demo：Nest 守卫 + Next ISR + PM2/Nginx。",
            ["Node.js", "React", "线上交付"],
        ),
        (
            "TypeScript 泛型与类型收窄你会怎么用？举一个让同事能看懂的例子",
            "用 ApiResult<T> + isRole 收窄；禁止 any；边界用 unknown 再收窄。强调可读类型比花哨类型重要。",
            ["TypeScript"],
        ),
        (
            "NestJS 里依赖注入、中间件、守卫分别解决什么问题？",
            "DI 管对象装配；Middleware 横切日志/限流；Guard 做鉴权授权。演示 AuthGuard + PermissionsGuard。",
            ["NestJS", "RBAC"],
        ),
        (
            "Next.js App Router 中 RSC 与 Client Component 边界怎么划？SSR/ISR/CSR 怎么选？",
            "SEO/首屏用 RSC+SSR/ISR；强交互强鉴权用 CSR。FRAME：首页 ISR60s，详情 ISR30s，/ops CSR。",
            ["Next.js"],
        ),
        (
            "什么时候加索引？如何用执行计划验证？事务如何保证一致性？",
            "高选择过滤+排序列建组合索引；EXPLAIN QUERY PLAN 验证；上传完成「组装+改状态」同事务。",
            ["SQL"],
        ),
        (
            "Linux 上 Nginx + PM2 如何部署与排障？",
            "端口→pm2 logs→nginx error.log→502/413。Nginx 分 / 与 /api/，注意 client_max_body_size。",
            ["Linux", "Nginx", "PM2"],
        ),
        (
            "HLS/CDN、SEO、分片上传、爬虫、PV/UV、RBAC 你会怎么串成一条业务故事？",
            "媒体运营：切片上 CDN；SSR+JSON-LD；multipart→OSS；采集退避；埋点口径；角色权限矩阵。",
            ["加分项"],
        ),
        (
            "硬性要求 Vibe coding：你如何用 AI 快速交付仍可维护的代码？",
            "先定边界与验收，再生成可运行闭环，补类型/守卫/文档；FRAME 仓库即交付物，强调可讲可扩。",
            ["Vibe coding"],
        ),
    ]
    nodes = []
    for q, a, tags in topics:
        child_q = f"追问：围绕「{tags[0]}」，结合 JD 再往下挖一层你会怎么答？"
        nodes.append(
            normalize_node(
                {
                    "question": q,
                    "answer": a + ("\n\n（离线种子；可联网用 DeepSeek 同步升级）"),
                    "tags": tags,
                    "source": "offline-seed",
                    "children": [
                        {
                            "question": child_q,
                            "answer": "先复述考点 → 给机制 → 给反例/排障 → 挂到 Demo 文件路径。",
                            "tags": tags,
                            "children": [],
                            "source": "offline-seed",
                        }
                    ],
                }
            )
        )
    title = "FRAME 岗位面试题树（离线种子）"
    if "Vibe" in jd or "Nest" in jd:
        title = "基于当前 JD 的面试题树（离线种子）"
    return normalize_tree({"title": title, "nodes": nodes})


def deep_copy_tree(tree: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(tree)


ProgressCb = Callable[[str], None]
