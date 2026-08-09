# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import shutil
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


def coerce_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[,，;/|]", raw) if any(ch in raw for ch in ",，;/|") else [raw]
        return [p.strip() for p in parts if p.strip()]
    if isinstance(raw, (list, tuple, set)):
        out: list[str] = []
        for t in raw:
            if t is None:
                continue
            s = str(t).strip()
            if s:
                out.append(s)
        return out
    return [str(raw).strip()] if str(raw).strip() else []


def coerce_children(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [c for c in raw if isinstance(c, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []


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


# ----- 多棵树管理（manifest: data/trees.json） -----


def trees_manifest_path() -> Path:
    return data_dir() / "trees.json"


def _default_manifest() -> dict[str, Any]:
    return {
        "current": "default",
        "trees": [{"id": "default", "title": "面试题树", "file": "interview_tree.json"}],
    }


def save_trees_manifest(manifest: dict[str, Any]) -> None:
    trees_manifest_path().write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_trees_manifest() -> dict[str, Any]:
    path = trees_manifest_path()
    if not path.exists():
        manifest = _default_manifest()
        # 迁移：保留旧 interview_tree.json 的标题
        if tree_path().exists():
            try:
                old = normalize_tree(json.loads(tree_path().read_text(encoding="utf-8")))
                manifest["trees"][0]["title"] = old.get("title") or "面试题树"
            except Exception:
                pass
        save_trees_manifest(manifest)
        return manifest
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        manifest = _default_manifest()
        save_trees_manifest(manifest)
        return manifest


def list_trees() -> list[dict[str, Any]]:
    return load_trees_manifest().get("trees") or []


def current_tree_id() -> str:
    return str(load_trees_manifest().get("current") or "default")


def tree_file_for(tree_id: str) -> Path:
    if tree_id == "default":
        return tree_path()
    return data_dir() / "trees" / f"{tree_id}.json"


def create_tree(title: str = "新题库") -> dict[str, Any]:
    manifest = load_trees_manifest()
    tid = f"t_{uuid.uuid4().hex[:10]}"
    entry = {"id": tid, "title": title, "file": f"trees/{tid}.json"}
    (manifest.setdefault("trees", [])).append(entry)
    manifest["current"] = tid
    save_trees_manifest(manifest)
    save_tree(empty_tree(title))
    return entry


def switch_tree(tree_id: str) -> None:
    manifest = load_trees_manifest()
    if not any(t.get("id") == tree_id for t in manifest.get("trees") or []):
        return
    manifest["current"] = tree_id
    save_trees_manifest(manifest)


def rename_tree(tree_id: str, title: str) -> None:
    manifest = load_trees_manifest()
    for t in manifest.get("trees") or []:
        if t.get("id") == tree_id:
            t["title"] = title
    save_trees_manifest(manifest)


def delete_tree(tree_id: str) -> None:
    manifest = load_trees_manifest()
    trees = manifest.get("trees") or []
    if len(trees) <= 1:
        raise ValueError("至少保留一棵题树")
    trees = [t for t in trees if t.get("id") != tree_id]
    manifest["trees"] = trees
    if manifest.get("current") == tree_id:
        manifest["current"] = trees[0]["id"]
    save_trees_manifest(manifest)
    path = tree_file_for(tree_id)
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass


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
    children = [normalize_node(c) for c in coerce_children(raw.get("children"))]
    return {
        "id": str(raw.get("id") or new_id()),
        "question": str(raw.get("question") or "").strip() or "（未命名问题）",
        "answer": str(raw.get("answer") or "").strip(),
        "tags": coerce_tags(raw.get("tags")),
        "children": children,
        "updated_at": str(raw.get("updated_at") or utc_now()),
        "source": str(raw.get("source") or "deepseek"),
    }


def normalize_tree(raw: dict[str, Any]) -> dict[str, Any]:
    nodes = [normalize_node(n) for n in (raw.get("nodes") or []) if isinstance(n, dict)]
    return {
        "version": int(raw.get("version") or 1),
        "title": str(raw.get("title") or "面试题树"),
        "jd": str(raw.get("jd") or ""),
        "updated_at": str(raw.get("updated_at") or utc_now()),
        "nodes": nodes,
    }


def load_tree() -> dict[str, Any]:
    path = tree_file_for(current_tree_id())
    if not path.exists():
        return empty_tree()
    return normalize_tree(json.loads(path.read_text(encoding="utf-8")))


def save_tree(tree: dict[str, Any]) -> None:
    tree = normalize_tree(tree)
    tree["updated_at"] = utc_now()
    path = tree_file_for(current_tree_id())
    # 自动备份上一版，防止写坏后全丢
    if path.exists():
        try:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        except Exception:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
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


def tree_outline(tree: dict[str, Any], limit: int = 40) -> str:
    lines: list[str] = []

    def walk_lines(nodes: list[dict[str, Any]], depth: int) -> None:
        for n in nodes:
            if len(lines) >= limit:
                return
            indent = "  " * depth
            lines.append(f"{indent}- {n.get('question') or ''}")
            walk_lines(n.get("children") or [], depth + 1)

    walk_lines(tree.get("nodes") or [], 0)
    if not lines:
        return "(空树)"
    more = ""
    # Count remaining roughly
    total = sum(1 for _ in walk(tree.get("nodes") or []))
    if total > limit:
        more = f"\n… 另有约 {total - limit} 题未列出"
    return "\n".join(lines) + more


def _norm_q(text: str) -> str:
    s = "".join(ch for ch in (text or "").lower() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    return s


def _questions_similar(a: str, b: str) -> bool:
    na, nb = _norm_q(a), _norm_q(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 8 and (na in nb or nb in na):
        return True
    # lightweight token overlap for Chinese/English mix
    if len(na) >= 12 and len(nb) >= 12:
        shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
        hit = sum(1 for i in range(0, len(shorter) - 3) if shorter[i : i + 4] in longer)
        return hit >= max(3, len(shorter) // 8)
    return False


def find_node_by_question(
    nodes: list[dict[str, Any]], question: str
) -> dict[str, Any] | None:
    for n in nodes:
        if _questions_similar(n.get("question") or "", question):
            return n
        hit = find_node_by_question(n.get("children") or [], question)
        if hit is not None:
            return hit
    return None


def _merge_unique_children(
    node: dict[str, Any], children: list[dict[str, Any]]
) -> int:
    existing = node.setdefault("children", [])
    added = 0
    for raw in children:
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("question") or "")
        if any(_questions_similar(c.get("question") or "", q) for c in existing):
            continue
        existing.append(normalize_node({**raw, "source": raw.get("source") or "deepseek-refresh"}))
        added += 1
    if added:
        node["updated_at"] = utc_now()
    return added


def merge_refresh_into_tree(
    tree: dict[str, Any], payload: dict[str, Any]
) -> dict[str, int]:
    """Append/supplement only — never deletes existing nodes."""
    stats = {"added": 0, "supplemented": 0, "child_added": 0}
    nodes = tree.setdefault("nodes", [])

    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        tree["title"] = title.strip()

    for upd in payload.get("updates") or []:
        if not isinstance(upd, dict):
            continue
        match_q = str(upd.get("match_question") or "").strip()
        if not match_q:
            continue
        node = find_node_by_question(nodes, match_q)
        if node is None:
            # treat unmatched update as a new root node if it has content
            q = match_q
            a = str(upd.get("answer_supplement") or "").strip()
            if q:
                nodes.append(
                    normalize_node(
                        {
                            "question": q,
                            "answer": a,
                            "tags": upd.get("tags_add") or [],
                            "children": upd.get("new_children") or [],
                            "source": "deepseek-refresh",
                        }
                    )
                )
                stats["added"] += 1
            continue

        supplement = str(upd.get("answer_supplement") or "").strip()
        if supplement:
            old = (node.get("answer") or "").strip()
            if supplement not in old:
                node["answer"] = f"{old}\n\n【补充】{supplement}".strip() if old else supplement
                node["updated_at"] = utc_now()
                node["source"] = "deepseek-refresh"
                stats["supplemented"] += 1

        tags_add = upd.get("tags_add") or upd.get("tags") or []
        if tags_add:
            merged = list(node.get("tags") or [])
            for ts in coerce_tags(tags_add):
                if ts and ts not in merged:
                    merged.append(ts)
            node["tags"] = merged

        kids = upd.get("new_children") or upd.get("children") or []
        if kids:
            stats["child_added"] += _merge_unique_children(node, coerce_children(kids))

    for raw in payload.get("new_nodes") or []:
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("question") or "").strip()
        if not q:
            continue
        if find_node_by_question(nodes, q) is not None:
            # already exists — merge children / supplement instead of duplicating root
            existing = find_node_by_question(nodes, q)
            assert existing is not None
            ans = str(raw.get("answer") or "").strip()
            if ans and ans not in (existing.get("answer") or ""):
                old = (existing.get("answer") or "").strip()
                existing["answer"] = f"{old}\n\n【补充】{ans}".strip() if old else ans
                existing["updated_at"] = utc_now()
                stats["supplemented"] += 1
            kids = raw.get("children") or raw.get("new_children") or []
            if kids:
                stats["child_added"] += _merge_unique_children(
                    existing, coerce_children(kids)
                )
            continue
        nodes.append(normalize_node({**raw, "source": "deepseek-refresh"}))
        stats["added"] += 1

    tree["updated_at"] = utc_now()
    return stats


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


def export_html(tree: dict[str, Any]) -> str:
    parts = [
        "<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'>",
        "<title>" + (tree.get("title") or "面试题树") + "</title>",
        "<style>",
        "body{font-family:'Microsoft YaHei','PingFang SC',sans-serif;line-height:1.7;max-width:880px;margin:32px auto;padding:0 20px;color:#1a1a1a}",
        "h1{border-bottom:2px solid #333;padding-bottom:8px}",
        "h2,h3,h4{margin-top:24px;color:#0b3d91}",
        ".tags{color:#667;font-size:.85em}",
        ".answer{white-space:pre-wrap;background:#f6f8fa;border-left:3px solid #0b3d91;padding:10px 14px;border-radius:4px}",
        "</style></head><body>",
    ]
    title = (tree.get("title") or "面试题树").replace("<", "&lt;")
    parts.append(f"<h1>{title}</h1>")
    jd = (tree.get("jd") or "").strip()
    if jd:
        esc = jd.replace("&", "&amp;").replace("<", "&lt;")
        parts.append(f"<h2>职位描述</h2><div class='answer'>{esc}</div>")

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render(nodes: list[dict[str, Any]], level: int) -> None:
        for n in nodes:
            tag = f"h{min(level + 2, 5)}"
            tags = ", ".join(n.get("tags") or [])
            parts.append(f"<{tag}>{esc(n.get('question'))}</{tag}>")
            if tags:
                parts.append(f"<div class='tags'>标签：{esc(tags)}</div>")
            parts.append(f"<div class='answer'>{esc(n.get('answer') or '（暂无答案）')}</div>")
            render(n.get("children") or [], level + 1)

    render(tree.get("nodes") or [], 0)
    parts.append("</body></html>")
    return "\n".join(parts)


def export_pdf(tree: dict[str, Any], path: str | Path) -> None:
    """导出 PDF（reportlab，内置 STSong 中文字体，无需额外字体文件）。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    h1 = ParagraphStyle("h1", fontName="STSong-Light", fontSize=22, leading=30, spaceAfter=10)
    h2 = ParagraphStyle("h2", fontName="STSong-Light", fontSize=16, leading=24, spaceBefore=12)
    h3 = ParagraphStyle("h3", fontName="STSong-Light", fontSize=14, leading=22, spaceBefore=10)
    h4 = ParagraphStyle("h4", fontName="STSong-Light", fontSize=12, leading=20, spaceBefore=8)
    body = ParagraphStyle(
        "body", fontName="STSong-Light", fontSize=11, leading=18, spaceBefore=4
    )

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    story = [Paragraph(esc(tree.get("title") or "面试题树"), h1)]
    jd = (tree.get("jd") or "").strip()
    if jd:
        story.append(Paragraph("职位描述", h2))
        for line in jd.splitlines():
            story.append(Paragraph(esc(line), body))

    def render(nodes: list[dict[str, Any]], level: int) -> None:
        for n in nodes:
            tag = (h2, h3, h4)[min(level, 2)]
            story.append(Paragraph(esc(n.get("question")), tag))
            tags = ", ".join(n.get("tags") or [])
            if tags:
                story.append(Paragraph(f"标签：{esc(tags)}", body))
            story.append(Paragraph(esc(n.get("answer") or "（暂无答案）"), body))
            story.append(Spacer(1, 3 * mm))
            render(n.get("children") or [], level + 1)

    render(tree.get("nodes") or [], 0)
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=str(tree.get("title") or "面试题树"))
    doc.build(story)


def filter_tree(tree: dict[str, Any], query: str) -> dict[str, Any]:
    """返回只含命中节点及其祖先的子集；query 为空返回整树深拷贝。"""
    q = (query or "").strip().lower()
    if not q:
        return deep_copy_tree(tree)

    def matches(n: dict[str, Any]) -> bool:
        return (
            q in (n.get("question") or "").lower()
            or q in (n.get("answer") or "").lower()
            or any(q in (t or "").lower() for t in (n.get("tags") or []))
        )

    def filter_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for n in nodes:
            children = filter_nodes(n.get("children") or [])
            if matches(n) or children:
                c = deepcopy(n)
                c["children"] = children
                out.append(c)
        return out

    result = deep_copy_tree(tree)
    result["nodes"] = filter_nodes(result.get("nodes") or [])
    return result


def tree_stats(tree: dict[str, Any]) -> dict[str, int]:
    nodes = list(walk(tree.get("nodes") or []))
    tags: set[str] = set()
    for n in nodes:
        tags.update(t for t in (n.get("tags") or []) if t)
    return {
        "total": len(nodes),
        "roots": len(tree.get("nodes") or []),
        "tags": len(tags),
    }


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
