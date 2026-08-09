# -*- coding: utf-8 -*-
"""FRAME 岗位面试题树 — DeepSeek 可生长桌面端（tkinter，无 Qt 依赖）。"""

from __future__ import annotations

import random
import re
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from defaults import DEFAULT_BASE_URL, DEFAULT_JD, DEFAULT_MODEL
from deepseek_client import chat, test_connection
from coding_lab import (
    LANG_LABELS,
    LANG_OPTIONS,
    STARTERS,
    normalize_lang,
    runtime_status,
    run_snippet,
    run_with_tests,
)
from prompts import (
    build_code_complete_messages,
    build_coding_messages,
    build_expand_messages,
    build_generate_messages,
    build_refresh_messages,
    build_sync_messages,
    parse_code_complete_payload,
    parse_coding_payload,
    parse_expand_payload,
    parse_generate_payload,
    parse_refresh_payload,
    parse_sync_payload,
)
from tree_store import (
    attach_children,
    create_tree,
    current_tree_id,
    delete_tree,
    ensure_coding_nodes,
    export_html,
    export_markdown,
    export_pdf,
    filter_tree,
    find_node,
    list_trees,
    load_config,
    load_tree,
    merge_refresh_into_tree,
    normalize_node,
    normalize_tree,
    path_to_node,
    rename_tree,
    replace_node_content,
    save_config,
    save_tree,
    seed_offline_tree,
    switch_tree,
    tree_outline,
    tree_path,
    tree_stats,
    walk,
)


def enable_windows_dpi_awareness() -> None:
    """Avoid blurry bitmap-scaled UI on HiDPI Windows displays."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        # Per-monitor v2 when available; fall back to system DPI aware.
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def pick_ui_font_family(root: tk.Misc) -> str:
    available = {name.lower(): name for name in tkfont.families(root)}
    for candidate in (
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "Segoe UI Variable",
        "Segoe UI",
        "PingFang SC",
        "Noto Sans CJK SC",
    ):
        if candidate.lower() in available:
            return available[candidate.lower()]
    return "TkDefaultFont"


class ToolTip:
    """Hover tip for buttons / controls."""

    def __init__(
        self,
        widget: tk.Misc,
        text: str,
        font: tkfont.Font | None = None,
        delay_ms: int = 350,
    ) -> None:
        self.widget = widget
        self.text = text
        self.font = font
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: object | None = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _hide(self, _event: object | None = None) -> None:
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None

    def _show(self) -> None:
        if self._tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        try:
            tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        tk.Label(
            tip,
            text=self.text,
            justify=tk.LEFT,
            background="#FFF8DC",
            foreground="#1a1a1a",
            relief=tk.SOLID,
            borderwidth=1,
            padx=10,
            pady=6,
            wraplength=420,
            font=self.font,
        ).pack()
        self._tip = tip


class DetailPopup(tk.Toplevel):
    """80% 屏幕大弹窗：查看/复制完整文本。"""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        text: str,
        font: tkfont.Font,
        *,
        on_ai_query: Callable[[str], None] | None = None,
        on_ai_metaphor: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title(title or "查看")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        x, y = (sw - w) // 2, (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(640, 420)
        self._text = text or ""

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        head = ttk.Frame(self)
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text=title or "", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        col = 1
        if on_ai_query is not None:
            ttk.Button(
                head,
                text="AI 查询",
                command=lambda: on_ai_query(self._text),
            ).grid(row=0, column=col, sticky="e", padx=4)
            col += 1
        if on_ai_metaphor is not None:
            ttk.Button(
                head,
                text="AI 比喻",
                command=lambda: on_ai_metaphor(self._text),
            ).grid(row=0, column=col, sticky="e", padx=4)
            col += 1
        ttk.Button(head, text="复制", command=lambda: self._copy(self._text)).grid(
            row=0, column=col, sticky="e"
        )
        ttk.Button(head, text="关闭", command=self.destroy).grid(
            row=0, column=col + 1, sticky="e", padx=(8, 0)
        )

        box = ttk.Frame(self)
        box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(4, 14))
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)
        txt = tk.Text(box, wrap=tk.WORD, font=font, state=tk.DISABLED)
        txt.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=txt.yview)
        sb.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=sb.set)
        txt.configure(state=tk.NORMAL)
        txt.insert("1.0", self._text)
        txt.configure(state=tk.DISABLED)
        self.txt = txt

    def _copy(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text or "")


# ----- 文本工具：重点提取 / 语音朗读 -----

_KEY_MARKERS = (
    "重点", "核心", "关键", "注意", "必须", "建议", "推荐", "千万",
    "避免", "原则", "结论", "总结", "踩坑", "坑", "机制", "原理",
    "因为", "所以", "确保", "容易", "典型", "最常见", "注意", "提示",
)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])\s*", text)
    return [p.strip() for p in parts if p.strip()]


def extract_key_points(text: str, max_points: int = 8) -> list[str]:
    """本地规则：优先要点行/编号行，再按关键词打分挑重点句。"""
    text = (text or "").strip()
    if not text:
        return []
    lines = [ln.strip() for ln in re.split(r"\n+", text) if ln.strip()]
    bullets: list[str] = []
    rest: list[str] = []
    for ln in lines:
        if re.match(r"^[-*•·]|\d+[\.\、\）)]|[①②③④⑤⑥⑦⑧⑨⑩]", ln):
            bullets.append(ln)
        else:
            rest.append(ln)
    sentences = [s for ln in rest for s in _split_sentences(ln)]
    scored: list[tuple[int, str]] = []
    for s in sentences:
        score = sum(1 for mk in _KEY_MARKERS if mk in s)
        score += min(len(s) // 40, 2)
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    picked = [s for _, s in scored[:max_points]]
    if not picked and not bullets:
        picked = sentences[:3]
    result: list[str] = []
    seen: set[str] = set()
    for item in bullets[:max_points] + picked:
        if item not in seen:
            seen.add(item)
            result.append(item)
        if len(result) >= max_points:
            break
    return result


def strip_for_speech(text: str) -> str:
    """朗读用：去掉标点，只保留汉字/字母/数字与空格。"""
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text or "", flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _tts_speak(text: str) -> None:
    """系统语音朗读（已去标点）。优先 SAPI（win32com），回退 pyttsx3。"""
    spoken = strip_for_speech(text)
    if not spoken:
        return
    last: Exception | None = None
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        try:
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            voice.Speak(spoken)
            return
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:  # noqa: BLE001
        last = e
    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(spoken)
        engine.runAndWait()
        return
    except Exception as e:  # noqa: BLE001
        last = e
    raise RuntimeError("未找到语音引擎（可运行 pip install pyttsx3 pywin32）") from last


def lookup_browser(term: str, timeout: int = 12) -> str:
    """浏览器侧摘要：Wikipedia + DuckDuckGo Instant Answer。"""
    import json
    import urllib.parse
    import urllib.request

    term = (term or "").strip()
    if not term:
        raise ValueError("查询词为空")

    headers = {"User-Agent": "FRAME-InterviewTree/1.0 (desktop; lookup)"}
    chunks: list[str] = []

    for lang in ("zh", "en"):
        url = (
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(term)
        )
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            extract = (data.get("extract") or "").strip()
            title = (data.get("title") or term).strip()
            if extract:
                chunks.append(f"【维基百科 · {title}】\n{extract}")
                break
        except Exception:
            continue

    ddg = (
        "https://api.duckduckgo.com/?"
        + urllib.parse.urlencode(
            {"q": term, "format": "json", "no_html": 1, "skip_disambig": 1}
        )
    )
    try:
        req = urllib.request.Request(ddg, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        abstract = (data.get("AbstractText") or data.get("Definition") or "").strip()
        if abstract:
            chunks.append(f"【DuckDuckGo】\n{abstract}")
        related = data.get("RelatedTopics") or []
        for item in related[:3]:
            if isinstance(item, dict) and item.get("Text"):
                chunks.append(f"· {item['Text']}")
            elif isinstance(item, dict) and isinstance(item.get("Topics"), list):
                for sub in item["Topics"][:2]:
                    if isinstance(sub, dict) and sub.get("Text"):
                        chunks.append(f"· {sub['Text']}")
    except Exception:
        pass

    if not chunks:
        raise RuntimeError(
            f"浏览器未查到「{term}」的简明摘要。可改用 AI 查询，或换更完整的英文术语。"
        )
    return "\n\n".join(chunks)


def expand_term_at(widget: tk.Text, index: str) -> str:
    """在点击位置向两侧扩展成词（中英数字混合）。"""
    line_s, col_s = index.split(".")
    line, col = int(line_s), int(col_s)
    text = widget.get(f"{line}.0", f"{line}.end")
    if not text:
        return ""
    if col >= len(text):
        col = max(0, len(text) - 1)

    def ok(ch: str) -> bool:
        return bool(ch) and (
            ch.isalnum() or "\u4e00" <= ch <= "\u9fff" or ch in "_-+./#"
        )

    if not ok(text[col]):
        return ""
    left = col
    while left > 0 and ok(text[left - 1]):
        left -= 1
    right = col + 1
    while right < len(text) and ok(text[right]):
        right += 1
    return text[left:right].strip(".-_/+#")


class LookupChooser(tk.Toplevel):
    """选择用 AI 还是浏览器查询某个词。"""

    def __init__(
        self,
        master: tk.Misc,
        term: str,
        on_ai: Callable[[], None],
        on_browser: Callable[[], None],
        font: tkfont.Font | None = None,
    ) -> None:
        super().__init__(master)
        self.title("选择查询方式")
        self.transient(master)
        self.resizable(False, False)
        self.grab_set()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 520, 220
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        ttk.Label(self, text=f"查询词：{term}", font=font).pack(
            padx=20, pady=(18, 8), anchor="w"
        )
        ttk.Label(
            self,
            text="请选择查询来源（确认后开始查询并展示结果）",
            font=font,
        ).pack(padx=20, pady=(0, 12), anchor="w")

        row = ttk.Frame(self)
        row.pack(fill=tk.X, padx=20, pady=8)
        row.columnconfigure((0, 1), weight=1)

        def pick_ai() -> None:
            self.destroy()
            on_ai()

        def pick_browser() -> None:
            self.destroy()
            on_browser()

        ttk.Button(row, text="AI 查询（DeepSeek）", command=pick_ai).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(row, text="浏览器查询", command=pick_browser).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )
        ttk.Button(self, text="取消", command=self.destroy).pack(pady=(4, 14))


class QuizWindow(tk.Toplevel):
    """刷题/背诵模式：只看题、点开看答案、随机抽题。"""

    def __init__(
        self,
        master: tk.Misc,
        nodes: list[dict[str, Any]],
        font_q: tkfont.Font,
        font_a: tkfont.Font,
        font_ui: tkfont.Font,
    ) -> None:
        super().__init__(master)
        self.title("刷题模式 · 面试题树")
        self.geometry("1180x760")
        self.minsize(900, 600)

        self._cards: list[dict[str, Any]] = [
            {"question": n.get("question") or "", "answer": n.get("answer") or ""}
            for n in walk(nodes)
            if (n.get("question") or "").strip()
        ]
        self._idx = -1
        self._revealed = False
        self._font_q = font_q
        self._font_a = font_a

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        top.columnconfigure(0, weight=1)
        self.progress = tk.StringVar(value="0 / 0")
        ttk.Label(top, textvariable=self.progress, font=font_ui).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            top,
            text="随机抽题",
            command=self.next_random,
        ).grid(row=0, column=1, sticky="e")

        card = ttk.Frame(self, padding=14)
        card.grid(row=1, column=0, sticky="nsew", padx=16, pady=6)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        ttk.Label(card, text="题目", font=self._font_q).grid(
            row=0, column=0, sticky="w"
        )
        self.q_text = tk.Text(
            card, height=5, wrap=tk.WORD, font=self._font_q, state=tk.DISABLED
        )
        self.q_text.grid(row=1, column=0, sticky="ew", pady=4)

        ans_head = ttk.Frame(card)
        ans_head.grid(row=2, column=0, sticky="nsew")
        ans_head.columnconfigure(0, weight=1)
        ans_head.rowconfigure(0, weight=1)
        ttk.Label(ans_head, text="参考答案（先自己口述再看）", font=self._font_q).grid(
            row=0, column=0, sticky="w"
        )
        self.btn_reveal = ttk.Button(ans_head, text="显示答案", command=self.toggle_answer)
        self.btn_reveal.grid(row=0, column=1, sticky="e")
        self.a_text = tk.Text(
            ans_head, wrap=tk.WORD, font=self._font_a, state=tk.DISABLED
        )
        self.a_text.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(6, 0))

        btns = ttk.Frame(self)
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        btns.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(btns, text="← 上一题", command=self.prev).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ttk.Button(btns, text="下一题 →", command=self.next_card).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(btns, text="关闭", command=self.destroy).grid(
            row=0, column=2, sticky="ew", padx=4
        )

        self.next_random()

    def _current(self) -> dict[str, Any] | None:
        if not self._cards or self._idx < 0:
            return None
        return self._cards[self._idx]

    def _show(self) -> None:
        card = self._current()
        if card is None:
            return
        self._revealed = False
        self.q_text.configure(state=tk.NORMAL)
        self.q_text.delete("1.0", tk.END)
        self.q_text.insert("1.0", card["question"])
        self.q_text.configure(state=tk.DISABLED)
        self.a_text.configure(state=tk.NORMAL)
        self.a_text.delete("1.0", tk.END)
        self.a_text.insert("1.0", "（点击「显示答案」再核对）")
        self.a_text.configure(state=tk.DISABLED)
        self.btn_reveal.configure(text="显示答案")
        self.progress.set(f"{self._idx + 1} / {len(self._cards)}")

    def toggle_answer(self) -> None:
        card = self._current()
        if card is None:
            return
        if not self._revealed:
            self._revealed = True
            self.a_text.configure(state=tk.NORMAL)
            self.a_text.delete("1.0", tk.END)
            self.a_text.insert("1.0", card["answer"] or "（暂无答案）")
            self.a_text.configure(state=tk.DISABLED)
            self.btn_reveal.configure(text="隐藏答案")
        else:
            self._revealed = False
            self.a_text.configure(state=tk.NORMAL)
            self.a_text.delete("1.0", tk.END)
            self.a_text.insert("1.0", "（点击「显示答案」再核对）")
            self.a_text.configure(state=tk.DISABLED)
            self.btn_reveal.configure(text="显示答案")

    def next_random(self) -> None:
        if not self._cards:
            return
        self._idx = random.randrange(len(self._cards))
        self._show()

    def prev(self) -> None:
        if not self._cards:
            return
        self._idx = (self._idx - 1) % len(self._cards)
        self._show()

    def next_card(self) -> None:
        if not self._cards:
            return
        self._idx = (self._idx + 1) % len(self._cards)
        self._show()


class CodingLabWindow(tk.Toplevel):
    """实操实验室：多语言编辑、DeepSeek 补全、运行、自测、看参考实现。"""

    def __init__(
        self,
        master: App,
        node: dict[str, Any],
        font_ui: tkfont.Font,
        font_code: tkfont.Font,
    ) -> None:
        super().__init__(master)
        self.master_app = master
        self.node = node
        self._font_ui = font_ui
        self.title(f"实操实验室 · {node.get('question') or '编程题'}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.85), int(sh * 0.85)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.minsize(960, 640)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        self._complete_busy = False
        self._complete_gen = 0
        self._idle_after: str | None = None
        self._ghost_text = ""
        self._ghost_index: str | None = None
        self._auto_complete = tk.BooleanVar(value=True)

        head = ttk.Frame(self)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 4))
        head.columnconfigure(0, weight=1)
        ttk.Label(
            head,
            text=node.get("question") or "实操题",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")

        lang_row = ttk.Frame(head)
        lang_row.grid(row=0, column=1, sticky="e", padx=(8, 8))
        ttk.Label(lang_row, text="语言").pack(side=tk.LEFT)
        self._lang_labels = [label for label, _ in LANG_OPTIONS]
        initial = normalize_lang(node.get("language") or "python")
        self.lang_var = tk.StringVar(value=LANG_LABELS.get(initial, "Python"))
        self.lang_combo = ttk.Combobox(
            lang_row,
            textvariable=self.lang_var,
            values=self._lang_labels,
            state="readonly",
            width=20,
            font=font_ui,
        )
        self.lang_combo.pack(side=tk.LEFT, padx=6)
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_lang_change)
        self.runtime_var = tk.StringVar(value="")
        ttk.Label(lang_row, textvariable=self.runtime_var, width=36).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Checkbutton(
            lang_row, text="自动补全", variable=self._auto_complete
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(head, text="关闭", command=self.destroy).grid(row=0, column=2, sticky="e")

        left = ttk.Frame(self, padding=8)
        left.grid(row=1, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="题目说明 / 考点", font=font_ui).grid(row=0, column=0, sticky="w")
        desc = tk.Text(left, height=10, wrap=tk.WORD, font=font_ui)
        desc.grid(row=1, column=0, sticky="nsew", pady=4)
        desc.insert(
            "1.0",
            (node.get("answer") or "")
            + (("\n\n提示：" + node["hint"]) if node.get("hint") else ""),
        )
        desc.configure(state=tk.DISABLED)

        ttk.Label(left, text="自测用例（需与当前语言匹配）", font=font_ui).grid(
            row=2, column=0, sticky="w", pady=(8, 2)
        )
        tests_box = tk.Text(left, height=8, wrap=tk.WORD, font=font_code)
        tests_box.grid(row=3, column=0, sticky="nsew")
        tests_box.insert("1.0", "\n".join(node.get("tests") or []) or "（无用例）")
        tests_box.configure(state=tk.DISABLED)
        left.rowconfigure(3, weight=1)

        right = ttk.Frame(self, padding=8)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=3)
        right.rowconfigure(3, weight=2)
        self.code_label = ttk.Label(right, text="你的代码", font=font_ui)
        self.code_label.grid(row=0, column=0, sticky="w")
        self.code = tk.Text(right, wrap=tk.NONE, font=font_code, undo=True)
        self.code.grid(row=1, column=0, sticky="nsew", pady=4)
        starter = node.get("starter_code") or STARTERS.get(initial, "")
        self.code.insert("1.0", starter)
        code_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.code.yview)
        code_scroll.grid(row=1, column=1, sticky="ns")
        self.code.configure(yscrollcommand=code_scroll.set)
        self.code.tag_configure("ghost", foreground="#8a8a8a")
        self.code.bind("<KeyRelease>", self._on_code_key)
        self.code.bind("<Button-1>", self._on_code_click)
        self.code.bind("<Control-space>", self._on_force_complete)
        self.code.bind("<Control-Key-space>", self._on_force_complete)
        self.code.bind("<Tab>", self._on_tab)
        self.code.bind("<Escape>", self._on_escape)
        self.code.bind("<<Paste>>", lambda _e: self.after(1, self._clear_ghost))

        btns = ttk.Frame(right)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        for i in range(5):
            btns.columnconfigure(i, weight=1)
        ttk.Button(btns, text="运行代码", command=self.on_run).grid(
            row=0, column=0, sticky="ew", padx=2
        )
        ttk.Button(btns, text="跑自测", command=self.on_test).grid(
            row=0, column=1, sticky="ew", padx=2
        )
        ttk.Button(btns, text="DeepSeek 补全", command=self.on_ai_complete).grid(
            row=0, column=2, sticky="ew", padx=2
        )
        ttk.Button(btns, text="重置模板", command=self.on_reset).grid(
            row=0, column=3, sticky="ew", padx=2
        )
        ttk.Button(btns, text="查看参考实现", command=self.on_solution).grid(
            row=0, column=4, sticky="ew", padx=2
        )

        ttk.Label(
            right,
            text="输出（Tab 接受灰字补全 · Esc 取消 · Ctrl+Space 立即补全）",
            font=font_ui,
        ).grid(row=3, column=0, sticky="w")
        self.out = tk.Text(right, wrap=tk.WORD, font=font_code, height=10)
        self.out.grid(row=4, column=0, columnspan=2, sticky="nsew")

        self._original_lang = initial
        self._refresh_lang_ui()

    def _current_lang(self) -> str:
        label = self.lang_var.get()
        for lab, lid in LANG_OPTIONS:
            if lab == label:
                return lid
        return "python"

    def _refresh_lang_ui(self) -> None:
        lang = self._current_lang()
        self.code_label.configure(text=f"你的代码（{LANG_LABELS.get(lang, lang)}）")
        ok, info = runtime_status(lang)
        short = str(info)
        if len(short) > 48:
            short = short[:45] + "…"
        self.runtime_var.set(("✓ " if ok else "✗ ") + short)

    def on_lang_change(self, _event: object | None = None) -> None:
        self._clear_ghost()
        lang = self._current_lang()
        self._refresh_lang_ui()
        cur = self.code.get("1.0", "end-1c").strip()
        old_starters = {s.strip() for s in STARTERS.values() if s}
        node_starter = (self.node.get("starter_code") or "").strip()
        if (not cur) or cur in old_starters or cur == node_starter:
            self.code.delete("1.0", tk.END)
            if lang == self._original_lang and node_starter:
                self.code.insert("1.0", node_starter)
            else:
                self.code.insert("1.0", STARTERS.get(lang, f"// {lang}\n"))
        self.status_note(f"已切换语言：{LANG_LABELS.get(lang, lang)}")

    def status_note(self, text: str) -> None:
        try:
            self.master_app.status.set(text)
        except Exception:
            pass

    def _set_out(self, text: str) -> None:
        self.out.delete("1.0", tk.END)
        self.out.insert("1.0", text)

    def _cancel_idle(self) -> None:
        if self._idle_after is not None:
            try:
                self.after_cancel(self._idle_after)
            except tk.TclError:
                pass
            self._idle_after = None

    def _clear_ghost(self) -> None:
        if self._ghost_index and self._ghost_text:
            end = self.code.index(f"{self._ghost_index}+{len(self._ghost_text)}c")
            self.code.delete(self._ghost_index, end)
        self._ghost_text = ""
        self._ghost_index = None

    def _on_code_click(self, _event: object | None = None) -> None:
        self._clear_ghost()

    def _on_code_key(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        # 导航/修饰键不触发；接受补全的键另处理
        if event.keysym in (
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
            "Tab",
            "Escape",
            "Up",
            "Down",
            "Left",
            "Right",
            "Home",
            "End",
            "Prior",
            "Next",
        ):
            return
        # 用户开始输入时清掉旧 ghost（KeyRelease 时 ghost 可能已在光标后）
        if self._ghost_text and event.keysym not in ("Tab",):
            # 若刚插入的字符落在 ghost 前，ghost 索引会偏移；直接清掉更稳
            self._clear_ghost()
        if not self._auto_complete.get():
            return
        if self._complete_busy:
            return
        self._cancel_idle()
        self._idle_after = self.after(1100, lambda: self._request_complete(force=False))

    def _on_force_complete(self, _event: object | None = None):
        self._request_complete(force=True)
        return "break"

    def _on_tab(self, _event: object | None = None):
        if self._ghost_text and self._ghost_index:
            # ghost 已是灰字显示在文档里：去掉 ghost 标签即可变成正式文本
            end = self.code.index(f"{self._ghost_index}+{len(self._ghost_text)}c")
            self.code.tag_remove("ghost", self._ghost_index, end)
            self.code.mark_set(tk.INSERT, end)
            self._ghost_text = ""
            self._ghost_index = None
            return "break"
        return None

    def _on_escape(self, _event: object | None = None):
        if self._ghost_text:
            self._clear_ghost()
            return "break"
        return None

    def _cursor_parts(self) -> tuple[str, str, str]:
        """返回 (prefix, suffix, insert_index)。若有 ghost，prefix/suffix 按真实代码算。"""
        insert = self.code.index(tk.INSERT)
        if self._ghost_index and self._ghost_text:
            # 光标通常在 ghost 前
            ghost_end = self.code.index(f"{self._ghost_index}+{len(self._ghost_text)}c")
            prefix = self.code.get("1.0", self._ghost_index)
            suffix = self.code.get(ghost_end, "end-1c")
            return prefix, suffix, self._ghost_index
        prefix = self.code.get("1.0", insert)
        suffix = self.code.get(insert, "end-1c")
        return prefix, suffix, insert

    def on_ai_complete(self) -> None:
        self._request_complete(force=True)

    def _request_complete(self, *, force: bool) -> None:
        self._cancel_idle()
        if self._complete_busy:
            if force:
                self.status_note("补全请求进行中…")
            return

        try:
            self.master_app._persist_cfg()
        except Exception:
            pass
        cfg = getattr(self.master_app, "cfg", None) or {}
        api_key = (cfg.get("api_key") or "").strip()
        if not api_key:
            if force:
                messagebox.showwarning(
                    "DeepSeek 补全", "请先在主窗口填写 DeepSeek API Key", parent=self
                )
            return

        prefix, suffix, insert = self._cursor_parts()
        if not force and not prefix.rstrip():
            return

        self._clear_ghost()
        lang = self._current_lang()
        self._complete_busy = True
        self._complete_gen += 1
        gen = self._complete_gen
        self.status_note("DeepSeek 代码补全中…")

        messages = build_code_complete_messages(
            language=lang,
            prefix=prefix,
            suffix=suffix,
            question=str(self.node.get("question") or ""),
            answer=str(self.node.get("answer") or ""),
            hint=str(self.node.get("hint") or ""),
        )
        base_url = cfg.get("base_url") or ""
        model = cfg.get("model") or ""

        def worker() -> None:
            try:
                raw = chat(
                    api_key=api_key,
                    messages=messages,
                    base_url=base_url,
                    model=model,
                    temperature=0.2,
                    timeout=60,
                    json_mode=True,
                    max_tokens=512,
                )
                text = parse_code_complete_payload(raw)
            except Exception as e:  # noqa: BLE001
                err = str(e)
                self.after(0, lambda: self._complete_fail(gen, err, force=force))
                return
            self.after(0, lambda: self._complete_ok(gen, text, insert))

        threading.Thread(target=worker, daemon=True).start()

    def _complete_fail(self, gen: int, err: str, *, force: bool) -> None:
        if gen != self._complete_gen:
            return
        self._complete_busy = False
        self.status_note("补全失败")
        if force:
            messagebox.showerror("DeepSeek 补全失败", err, parent=self)

    def _complete_ok(self, gen: int, completion: str, insert_at: str) -> None:
        if gen != self._complete_gen:
            return
        self._complete_busy = False
        text = (completion or "").replace("\r\n", "\n").replace("\r", "\n")
        if not text:
            self.status_note("无需补全")
            return
        # 若用户已移动光标，尽量仍插在原位置；若文档变了则插当前光标
        try:
            pos = insert_at
            self.code.index(pos)
        except tk.TclError:
            pos = self.code.index(tk.INSERT)
        self._clear_ghost()
        self.code.insert(pos, text, ("ghost",))
        self._ghost_index = pos
        self._ghost_text = text
        self.code.mark_set(tk.INSERT, pos)
        self.status_note("已给出补全建议（Tab 接受 / Esc 取消）")

    def on_run(self) -> None:
        self._clear_ghost()
        lang = self._current_lang()
        ok, info = runtime_status(lang)
        if not ok:
            self._set_out(str(info))
            messagebox.showwarning("运行环境不可用", str(info), parent=self)
            return
        r = run_snippet(lang, self.code.get("1.0", "end-1c"))
        parts = [
            f"language={lang}",
            f"exit={r['returncode']}",
            "--- stdout ---",
            r.get("stdout") or "(空)",
            "--- stderr ---",
            r.get("stderr") or "(空)",
        ]
        self._set_out("\n".join(parts))

    def on_test(self) -> None:
        self._clear_ghost()
        lang = self._current_lang()
        node_lang = self._original_lang
        tests = self.node.get("tests") or []
        if not tests:
            messagebox.showinfo("跑自测", "本题没有自测用例，可直接「运行代码」。", parent=self)
            return
        if lang != node_lang:
            if not messagebox.askyesno(
                "语言不一致",
                f"本题自测用例按「{LANG_LABELS.get(node_lang, node_lang)}」编写，"
                f"当前选择是「{LANG_LABELS.get(lang, lang)}」。\n仍要尝试跑自测吗？",
                parent=self,
            ):
                return
        ok, info = runtime_status(lang)
        if not ok:
            self._set_out(str(info))
            messagebox.showwarning("运行环境不可用", str(info), parent=self)
            return
        r = run_with_tests(self.code.get("1.0", "end-1c"), tests, lang=lang)
        lines = [f"语言：{lang}", f"结果：{r['passed']}/{r['total']} 通过"]
        for d in r.get("details") or []:
            mark = "✓" if d["ok"] else "✗"
            lines.append(f"{mark} #{d['index']} {d['test'][:80]}")
            if not d["ok"]:
                lines.append(f"    → {d['message']}")
        self._set_out("\n".join(lines))
        if r.get("ok"):
            messagebox.showinfo("自测通过", f"全部 {r['total']} 条用例通过！", parent=self)

    def on_reset(self) -> None:
        self._clear_ghost()
        lang = self._current_lang()
        self.code.delete("1.0", tk.END)
        if lang == self._original_lang and self.node.get("starter_code"):
            self.code.insert("1.0", self.node.get("starter_code") or "")
        else:
            self.code.insert("1.0", STARTERS.get(lang, f"// {lang}\n"))

    def on_solution(self) -> None:
        self._clear_ghost()
        lang = self._current_lang()
        if lang != self._original_lang:
            messagebox.showinfo(
                "参考实现",
                f"参考实现属于「{LANG_LABELS.get(self._original_lang, self._original_lang)}」，"
                "请先把语言切回该语言再查看。",
                parent=self,
            )
            return
        sol = (self.node.get("solution_code") or "").strip()
        if not sol:
            messagebox.showinfo("参考实现", "本题暂无参考实现", parent=self)
            return
        if not messagebox.askyesno(
            "查看参考实现", "将把参考实现填入编辑器（可先另存你的代码）。继续？", parent=self
        ):
            return
        self.code.delete("1.0", tk.END)
        self.code.insert("1.0", sol)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FRAME 面试题树 · DeepSeek")

        self.tree_data = load_tree()
        self.cfg = load_config()
        if not self.cfg.get("jd_text"):
            self.cfg["jd_text"] = DEFAULT_JD

        self._busy = False
        self._iid_to_id: dict[str, str] = {}
        self._id_to_iid: dict[str, str] = {}
        self._undo_snapshot: dict[str, Any] | None = None
        self._filter_query = ""
        self._task_start = 0.0
        self._ticker_id: str | None = None
        self._speaking = False
        self._term_cache: dict[str, str] = {}
        self._term_tip_win: tk.Toplevel | None = None
        self._hover_fetching: set[str] = set()

        self._setup_fonts()
        self._build_ui()
        self._load_jd_from_tree()
        added_coding = ensure_coding_nodes(self.tree_data)
        if added_coding:
            self._save_current_tree()
        self._reload_tree()
        self._reload_tree_switcher()
        if added_coding:
            self.status.set(f"已自动追加 {added_coding} 道离线实操题（可开「实操实验室」）")
        else:
            self.status.set(f"本地文件：{tree_path()}")

        if not (self.tree_data.get("nodes") or []):
            self.on_offline_seed()

    def _setup_fonts(self) -> None:
        family = pick_ui_font_family(self)
        # Labels / buttons
        self.font_ui = tkfont.Font(family=family, size=20)
        self.font_ui_bold = tkfont.Font(family=family, size=21, weight="bold")
        self.font_tree = tkfont.Font(family=family, size=20)
        self.font_status = tkfont.Font(family=family, size=18)
        self.font_tip = tkfont.Font(family=family, size=16)
        # Inputs: larger than labels — ttk.Entry ignores Style font on Windows,
        # so we also bump Tk named fonts and use tk.Entry/Text with this font.
        self.font_input = tkfont.Font(family=family, size=24)
        self.font_body = self.font_input

        for name, size in (
            ("TkDefaultFont", 20),
            ("TkTextFont", 24),
            ("TkFixedFont", 22),
            ("TkHeadingFont", 21),
            ("TkMenuFont", 20),
            ("TkCaptionFont", 18),
            ("TkSmallCaptionFont", 16),
            ("TkTooltipFont", 16),
            ("TkIconFont", 20),
        ):
            try:
                tkfont.nametofont(name).configure(family=family, size=size)
            except tk.TclError:
                pass

        style = ttk.Style(self)
        try:
            style.theme_use("clam")  # respects Entry/Spinbox font better than vista
        except tk.TclError:
            try:
                style.theme_use("vista")
            except tk.TclError:
                try:
                    style.theme_use("winnative")
                except tk.TclError:
                    pass

        style.configure(".", font=self.font_ui)
        style.configure("TLabel", font=self.font_ui)
        style.configure("TButton", font=self.font_ui, padding=(10, 5))
        style.configure("TEntry", font=self.font_input)
        style.configure("TSpinbox", font=self.font_input)
        style.configure("Treeview", font=self.font_tree, rowheight=50)
        style.configure("Treeview.Heading", font=self.font_ui_bold)
        style.configure("Title.TLabel", font=self.font_ui_bold)
        style.configure("Card.TFrame", relief="solid", borderwidth=1)

    def _tip(self, widget: tk.Misc, text: str) -> None:
        ToolTip(widget, text, font=self.font_tip)

    def _button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], Any],
        tip: str,
    ) -> ttk.Button:
        btn = ttk.Button(parent, text=text, command=command)
        self._tip(btn, tip)
        return btn

    # ----- UI -----
    def _build_ui(self) -> None:
        # Width +40% vs previous 440/480/1480
        LEFT_W = 616
        RIGHT_W = 672

        self.geometry("2072x920")
        self.minsize(1792, 800)
        try:
            self.tk.call("tk", "scaling", 1.0)
        except tk.TclError:
            pass

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        body = ttk.Frame(self)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0, minsize=LEFT_W)
        body.columnconfigure(1, weight=1, minsize=588)
        body.columnconfigure(2, weight=0, minsize=RIGHT_W)
        body.rowconfigure(0, weight=1)

        # Fixed-width side panels (grid_propagate False keeps size stable)
        left = ttk.Frame(body, style="Card.TFrame", padding=8, width=LEFT_W)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)
        left.configure(width=LEFT_W)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)  # JD text grows within left only

        mid = ttk.Frame(body, style="Card.TFrame", padding=8)
        mid.grid(row=0, column=1, sticky="nsew", padx=4, pady=8)
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(3, weight=1)

        right = ttk.Frame(body, style="Card.TFrame", padding=8, width=RIGHT_W)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_propagate(False)
        right.configure(width=RIGHT_W)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(4, weight=1)  # answer box expands within right panel only

        # ---- left: config + JD + actions ----
        ttk.Label(left, text="DeepSeek 接入", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        form = ttk.Frame(left)
        form.grid(row=1, column=0, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="API Key").grid(row=0, column=0, sticky="w")
        self.api_key = tk.Entry(form, show="*", font=self.font_input)
        self.api_key.insert(0, self.cfg.get("api_key", ""))
        self.api_key.grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0), ipady=4)
        ttk.Label(form, text="Base URL").grid(row=1, column=0, sticky="w")
        self.base_url = tk.Entry(form, font=self.font_input)
        self.base_url.insert(0, self.cfg.get("base_url") or DEFAULT_BASE_URL)
        self.base_url.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0), ipady=4)
        ttk.Label(form, text="Model").grid(row=2, column=0, sticky="w")
        self.model = tk.Entry(form, font=self.font_input)
        self.model.insert(0, self.cfg.get("model") or DEFAULT_MODEL)
        self.model.grid(row=2, column=1, sticky="ew", pady=2, padx=(6, 0), ipady=4)
        self._button(
            form,
            "测试连接",
            self.on_test,
            "用当前 API Key / Base URL / Model 向 DeepSeek 发一条探测请求，确认能连通。",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        jd_header = ttk.Frame(left)
        jd_header.grid(row=2, column=0, sticky="ew", pady=(8, 2))
        jd_header.columnconfigure(0, weight=1)
        ttk.Label(jd_header, text="职位描述", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._button(
            jd_header,
            "弹窗",
            lambda: self._open_detail("职位描述", self.jd_edit.get("1.0", "end-1c")),
            "在新窗口（80% 屏幕）查看职位描述完整内容；双击输入框也可打开。",
        ).grid(row=0, column=1, sticky="e", padx=2)
        self._button(
            jd_header,
            "一键粘贴",
            self.on_paste_jd,
            "用系统剪贴板内容整段替换职位描述框（先复制 JD，再点此按钮）。",
        ).grid(row=0, column=2, sticky="e", padx=2)
        self.btn_extra_toggle = self._button(
            jd_header,
            "补充 ▾",
            self.on_toggle_extra,
            "展开/收起「生成补充说明」输入区（默认隐藏，避免挤压职位描述）。",
        )
        self.btn_extra_toggle.grid(row=0, column=3, sticky="e")

        jd_box = ttk.Frame(left)
        jd_box.grid(row=3, column=0, sticky="nsew")
        jd_box.columnconfigure(0, weight=1)
        jd_box.rowconfigure(0, weight=1)
        self.jd_edit = tk.Text(
            jd_box, wrap=tk.WORD, font=self.font_input, undo=True, height=8, width=36
        )
        self.jd_edit.insert("1.0", self.cfg.get("jd_text") or DEFAULT_JD)
        self.jd_edit.grid(row=0, column=0, sticky="nsew")
        jd_scroll = ttk.Scrollbar(jd_box, orient=tk.VERTICAL, command=self.jd_edit.yview)
        jd_scroll.grid(row=0, column=1, sticky="ns")
        self.jd_edit.configure(yscrollcommand=jd_scroll.set)
        self._bind_double_open(self.jd_edit, "职位描述")

        # 补充说明：默认隐藏，点「补充」才展开
        self._extra_visible = False
        self.extra_header = ttk.Frame(left)
        self.extra_header.columnconfigure(0, weight=1)
        ttk.Label(self.extra_header, text="生成补充说明（可选）").grid(
            row=0, column=0, sticky="w"
        )
        self._button(
            self.extra_header,
            "弹窗",
            lambda: self._open_detail("生成补充说明", self.extra_edit.get("1.0", "end-1c")),
            "在新窗口（80% 屏幕）查看补充说明；双击输入框也可打开。",
        ).grid(row=0, column=1, sticky="e")
        self.extra_edit = tk.Text(
            left, height=3, wrap=tk.WORD, font=self.font_input, undo=True, width=36
        )
        self._bind_double_open(self.extra_edit, "生成补充说明")
        # 不 grid，默认不显示

        spin_row = ttk.Frame(left)
        spin_row.grid(row=6, column=0, sticky="ew", pady=6)
        ttk.Label(spin_row, text="每次展开子题数").pack(side=tk.LEFT)
        self.expand_count = tk.IntVar(value=3)
        spin = tk.Spinbox(
            spin_row,
            from_=1,
            to=6,
            textvariable=self.expand_count,
            width=5,
            font=self.font_input,
        )
        spin.pack(side=tk.LEFT, padx=6)
        self._tip(spin, "点击「展开选中节点」时，一次向该题追加的子追问数量（1–6）。")

        actions = ttk.Frame(left)
        actions.grid(row=7, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        self.btn_generate = self._button(
            actions,
            "① 解析 JD 并生成题树",
            self.on_generate,
            "根据左侧职位描述调用 DeepSeek，生成全新一级（含少量二级）面试题树并覆盖本地题树。",
        )
        self.btn_generate.grid(row=0, column=0, sticky="ew", pady=1)
        self.btn_offline = self._button(
            actions,
            "离线种子树",
            self.on_offline_seed,
            "不调用网络，用内置模板按当前 JD 生成一棵可练手的种子题树（可稍后联网同步升级）。",
        )
        self.btn_offline.grid(row=1, column=0, sticky="ew", pady=1)
        self.btn_expand = self._button(
            actions,
            "② 展开选中节点（生长）",
            self.on_expand,
            "对中间树里当前选中的题目，向 DeepSeek 追问并追加子节点（向下生长）。",
        )
        self.btn_expand.grid(row=2, column=0, sticky="ew", pady=1)
        self.btn_sync = self._button(
            actions,
            "③ 联网同步选中节点",
            self.on_sync,
            "用 DeepSeek 重写/补强当前选中节点的答案，并可追加新的子题。",
        )
        self.btn_sync.grid(row=3, column=0, sticky="ew", pady=1)
        self.btn_refresh = self._button(
            actions,
            "④ 刷新题树（追加/补充，不删除）",
            self.on_refresh,
            "对照整棵现有题树做增量刷新：只追加新题、补充答案与子题，绝不删除已有内容。",
        )
        self.btn_refresh.grid(row=4, column=0, sticky="ew", pady=1)
        self.btn_coding = self._button(
            actions,
            "⑤ 生成实操编程题（追加）",
            self.on_generate_coding,
            "按 JD 生成可手写的 Python 实操题并追加到题树（不删除原有口述题）。",
        )
        self.btn_coding.grid(row=5, column=0, sticky="ew", pady=1)
        self.btn_undo = self._button(
            actions,
            "↩ 撤销上次刷新",
            self.on_undo_refresh,
            "把整棵题树回滚到上一次刷新之前的状态（仅记录最近一次）。",
        )
        self.btn_undo.grid(row=6, column=0, sticky="ew", pady=1)
        self.btn_undo.configure(state=tk.DISABLED)

        save_row = ttk.Frame(actions)
        save_row.grid(row=7, column=0, sticky="ew", pady=(4, 0))
        save_row.columnconfigure(0, weight=1)
        save_row.columnconfigure(1, weight=1)
        self.btn_save = self._button(
            save_row,
            "保存到本地",
            self.on_save,
            "把 API 配置、职位描述与整棵面试题树写入本地 data/ 目录。",
        )
        self.btn_save.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.btn_export = self._button(
            save_row,
            "导出 Markdown",
            self.on_export,
            "把当前题树导出为 Markdown 文件，方便打印或背题。",
        )
        self.btn_export.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        export_row = ttk.Frame(actions)
        export_row.grid(row=8, column=0, sticky="ew", pady=(4, 0))
        export_row.columnconfigure(0, weight=1)
        export_row.columnconfigure(1, weight=1)
        self.btn_export_html = self._button(
            export_row,
            "导出 HTML",
            self.on_export_html,
            "导出带排版样式、可直接用浏览器打开的 HTML 文件。",
        )
        self.btn_export_html.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.btn_export_pdf = self._button(
            export_row,
            "导出 PDF",
            self.on_export_pdf,
            "导出 PDF 文档（内置中文字体，无需额外安装）。",
        )
        self.btn_export_pdf.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # ---- mid: tree ----
        mid_head = ttk.Frame(mid)
        mid_head.grid(row=0, column=0, sticky="ew")
        mid_head.columnconfigure(0, weight=1)
        ttk.Label(mid_head, text="面试题树", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._button(
            mid_head,
            "刷题模式",
            self.on_quiz,
            "隐藏答案逐题背诵：随机抽题 / 上一题 / 下一题，点一下才显示答案。",
        ).grid(row=0, column=1, sticky="e", padx=4)
        self._button(
            mid_head,
            "实操实验室",
            self.on_open_coding_lab,
            "打开当前选中的【实操】编程题，在内置编辑器写代码并跑自测。",
        ).grid(row=0, column=2, sticky="e", padx=4)
        self._button(
            mid_head,
            "刷新（追加补充）",
            self.on_refresh,
            "与左侧「④ 刷新题树」相同：增量追加/补充，不删除原有题目。",
        ).grid(row=0, column=3, sticky="e")

        # 题库切换 + 搜索
        tree_bar = ttk.Frame(mid)
        tree_bar.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        tree_bar.columnconfigure(1, weight=1)
        ttk.Label(tree_bar, text="题库").grid(row=0, column=0, sticky="w")
        self.tree_combo = ttk.Combobox(
            tree_bar, state="readonly", font=self.font_ui
        )
        self.tree_combo.grid(row=0, column=1, sticky="ew", padx=6)
        self.tree_combo.bind("<<ComboboxSelected>>", self.on_switch_tree)
        self._button(
            tree_bar,
            "新建",
            self.on_new_tree,
            "新建一棵独立题库（每棵树有各自的题目与职位描述）。",
        ).grid(row=0, column=2, sticky="e", padx=2)
        self._button(
            tree_bar,
            "重命名",
            self.on_rename_tree,
            "给当前题库重命名。",
        ).grid(row=0, column=3, sticky="e", padx=2)
        self._button(
            tree_bar,
            "删除",
            self.on_delete_tree,
            "删除当前题库（至少保留一棵；操作会先确认）。",
        ).grid(row=0, column=4, sticky="e", padx=2)

        search_bar = ttk.Frame(mid)
        search_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        search_bar.columnconfigure(1, weight=1)
        ttk.Label(search_bar, text="搜索").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_bar, textvariable=self.search_var, font=self.font_input
        )
        search_entry.grid(row=0, column=1, sticky="ew", padx=6, ipady=2)
        self.search_entry = search_entry
        self._tip(search_entry, "按题干 / 答案 / 标签过滤整棵树（回车清空）。")
        search_entry.bind("<KeyRelease>", self.on_search_change)
        search_entry.bind("<Return>", lambda _e: self.search_var.set("") or self.on_search_change())

        tree_wrap = ttk.Frame(mid)
        tree_wrap.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("tags", "kids"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="问题")
        self.tree.heading("tags", text="标签")
        self.tree.heading("kids", text="子节点")
        self.tree.column("#0", width=504, minwidth=280, stretch=True)
        self.tree.column("tags", width=168, minwidth=112, stretch=False)
        self.tree.column("kids", width=90, minwidth=67, stretch=False, anchor="center")
        ysb = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(tree_wrap, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select())

        # ---- right: editor ----
        ttk.Label(right, text="当前节点", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        q_header = ttk.Frame(right)
        q_header.grid(row=1, column=0, sticky="ew", pady=(6, 2))
        q_header.columnconfigure(0, weight=1)
        ttk.Label(q_header, text="问题").grid(row=0, column=0, sticky="w")
        self._button(
            q_header,
            "弹窗",
            lambda: self._open_detail("问题", self.q_edit.get("1.0", "end-1c")),
            "在新窗口（80% 屏幕）查看问题完整内容；双击输入框也可打开。",
        ).grid(row=0, column=1, sticky="e")
        self.q_edit = tk.Text(
            right, height=4, wrap=tk.WORD, font=self.font_input, undo=True, width=40
        )
        self.q_edit.grid(row=2, column=0, sticky="ew")
        self._bind_double_open(self.q_edit, "问题")

        ans_header = ttk.Frame(right)
        ans_header.grid(row=3, column=0, sticky="ew", pady=(6, 2))
        ans_header.columnconfigure(0, weight=1)
        ttk.Label(ans_header, text="参考答案").grid(row=0, column=0, sticky="w")
        self._button(
            ans_header,
            "弹窗",
            lambda: self._open_detail(
                "参考答案",
                self.a_edit.get("1.0", "end-1c"),
                answer_tools=True,
            ),
            "在新窗口（80% 屏幕）查看答案完整内容；双击词可划词查询。",
        ).grid(row=0, column=1, sticky="e", padx=4)
        self._button(
            ans_header,
            "查看重点",
            self.on_key_points,
            "从答案中提取重点句/要点，在新窗口一键查看（本地规则，无需联网）。",
        ).grid(row=0, column=2, sticky="e", padx=2)
        self._button(
            ans_header,
            "查询",
            self.on_lookup_selection,
            "先在答案里划选名词/术语，再点此按钮；也可双击词，或右键选择 AI / 浏览器查询。",
        ).grid(row=0, column=3, sticky="e", padx=2)
        self._button(
            ans_header,
            "朗读",
            self.on_speak,
            "用系统语音朗读当前答案（自动跳过标点符号）。",
        ).grid(row=0, column=4, sticky="e")
        ans_box = ttk.Frame(right)
        ans_box.grid(row=4, column=0, sticky="nsew")
        right.rowconfigure(4, weight=1)
        ans_box.columnconfigure(0, weight=1)
        ans_box.rowconfigure(0, weight=1)
        self.a_edit = tk.Text(
            ans_box, wrap=tk.WORD, font=self.font_input, undo=True, width=40, height=12
        )
        self.a_edit.grid(row=0, column=0, sticky="nsew")
        ans_scroll = ttk.Scrollbar(ans_box, orient=tk.VERTICAL, command=self.a_edit.yview)
        ans_scroll.grid(row=0, column=1, sticky="ns")
        self.a_edit.configure(yscrollcommand=ans_scroll.set)
        self._setup_answer_lookup(self.a_edit)

        tags_header = ttk.Frame(right)
        tags_header.grid(row=5, column=0, sticky="ew", pady=(6, 2))
        tags_header.columnconfigure(0, weight=1)
        ttk.Label(tags_header, text="标签（逗号分隔）").grid(row=0, column=0, sticky="w")
        self._button(
            tags_header,
            "AI 查询",
            lambda: self.on_ai_explain_answer(),
            "用 DeepSeek 解释当前参考答案：要点、为什么这样答、常见踩坑。",
        ).grid(row=0, column=1, sticky="e", padx=4)
        self._button(
            tags_header,
            "AI 比喻",
            lambda: self.on_ai_metaphor_answer(),
            "用通俗比喻讲解当前参考答案，帮助记忆与口述。",
        ).grid(row=0, column=2, sticky="e")
        self.tags_edit = tk.Entry(right, font=self.font_input)
        self.tags_edit.grid(row=6, column=0, sticky="ew", ipady=4)

        right_btns = ttk.Frame(right)
        right_btns.grid(row=7, column=0, sticky="ew", pady=(8, 0))
        right_btns.columnconfigure(0, weight=1)
        self._button(
            right_btns,
            "写回当前节点（本地）",
            self.on_apply,
            "把右侧编辑的问题、答案、标签写回选中节点，并立即保存到本地。",
        ).grid(row=0, column=0, sticky="ew", pady=1)
        self._button(
            right_btns,
            "删除当前节点",
            self.on_delete,
            "删除中间树中当前选中的节点及其全部子节点（会先确认）。",
        ).grid(row=1, column=0, sticky="ew", pady=1)
        copy_row = ttk.Frame(right_btns)
        copy_row.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        copy_row.columnconfigure(0, weight=1)
        copy_row.columnconfigure(1, weight=1)
        self._button(
            copy_row,
            "复制答案",
            self.on_copy_answer,
            "把当前选中节点的答案复制到剪贴板（快捷键 Ctrl+Shift+A）。",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self._button(
            copy_row,
            "复制问答",
            self.on_copy_qa,
            "把当前选中节点的「问题+答案」一起复制到剪贴板（Ctrl+Shift+C）。",
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        self.status = tk.StringVar(value="ready")
        self.stats_var = tk.StringVar(value="")
        status_bar = ttk.Frame(self)
        status_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(
            status_bar, textvariable=self.status, anchor="w", font=self.font_status
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            status_bar,
            textvariable=self.stats_var,
            anchor="e",
            font=self.font_status,
            foreground="#0b5cad",
        ).grid(row=0, column=1, sticky="e")
        self.rowconfigure(1, weight=0)

        # 全局快捷键
        self.bind_all("<Control-Shift-c>", lambda _e: self.on_copy_qa())
        self.bind_all("<Control-Shift-a>", lambda _e: self.on_copy_answer())
        self.bind_all("<Control-f>", lambda _e: self._focus_search())
        self.bind_all("<F5>", lambda _e: self.on_refresh())

    # ----- helpers -----
    def on_toggle_extra(self) -> None:
        self._extra_visible = not self._extra_visible
        if self._extra_visible:
            self.extra_header.grid(row=4, column=0, sticky="ew", pady=(6, 2))
            self.extra_edit.grid(row=5, column=0, sticky="ew")
            self.btn_extra_toggle.configure(text="补充 ▴")
            self.status.set("已展开补充说明输入区")
        else:
            self.extra_header.grid_remove()
            self.extra_edit.grid_remove()
            self.btn_extra_toggle.configure(text="补充 ▾")
            self.status.set("已收起补充说明输入区")

    def on_paste_jd(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("剪贴板为空", "请先复制职位描述，再点「一键粘贴」")
            return
        text = (text or "").strip()
        if not text:
            messagebox.showwarning("剪贴板为空", "请先复制职位描述，再点「一键粘贴」")
            return
        self.jd_edit.delete("1.0", tk.END)
        self.jd_edit.insert("1.0", text)
        self._persist_cfg()
        self.status.set(f"已粘贴职位描述（{len(text)} 字）")

    def _persist_cfg(self) -> None:
        self.cfg = {
            "api_key": self.api_key.get().strip(),
            "base_url": self.base_url.get().strip() or DEFAULT_BASE_URL,
            "model": self.model.get().strip() or DEFAULT_MODEL,
            "jd_text": self.jd_edit.get("1.0", "end-1c"),
        }
        save_config(self.cfg)

    # ----- 多棵树 / 搜索 / 统计 -----
    def _load_jd_from_tree(self) -> None:
        jd = (self.tree_data.get("jd") or "").strip()
        if jd:
            self.jd_edit.delete("1.0", tk.END)
            self.jd_edit.insert("1.0", jd)

    def _save_current_tree(self) -> None:
        self.tree_data["jd"] = self.jd_edit.get("1.0", "end-1c")
        save_tree(self.tree_data)

    def _reload_tree_switcher(self) -> None:
        trees = list_trees()
        self._tree_entries = trees
        self.tree_combo["values"] = [t.get("title") or "未命名" for t in trees]
        current = current_tree_id()
        for i, t in enumerate(trees):
            if t.get("id") == current:
                self.tree_combo.current(i)
                break

    def _current_tree_entry(self) -> dict[str, Any]:
        entries = getattr(self, "_tree_entries", None)
        if not entries:
            entries = list_trees()
            self._tree_entries = entries
        current = current_tree_id()
        for t in entries:
            if t.get("id") == current:
                return t
        return {"id": current, "title": "未命名", "file": ""}

    def on_switch_tree(self, _event: object | None = None) -> None:
        idx = self.tree_combo.current()
        entries = getattr(self, "_tree_entries", None) or list_trees()
        if not (0 <= idx < len(entries)):
            return
        tid = entries[idx]["id"]
        if tid == current_tree_id():
            return
        self._save_current_tree()
        switch_tree(tid)
        self.tree_data = load_tree()
        self._undo_snapshot = None
        self.btn_undo.configure(state=tk.DISABLED)
        self._filter_query = ""
        self.search_var.set("")
        self._load_jd_from_tree()
        self._reload_tree()
        self._reload_tree_switcher()
        self._update_stats()
        self.status.set(f"已切换到题库：{self._current_tree_entry().get('title')}")

    def on_new_tree(self) -> None:
        title = "新题库"
        # 简单弹窗输入标题
        dialog = tk.Toplevel(self)
        dialog.title("新建题库")
        dialog.geometry("480x180")
        dialog.transient(self)
        ttk.Label(dialog, text="题库标题：", font=self.font_ui).pack(padx=16, pady=(20, 6))
        var = tk.StringVar(value=f"{title} {len(list_trees()) + 1}")
        entry = tk.Entry(dialog, textvariable=var, font=self.font_input)
        entry.pack(fill=tk.X, padx=16)
        entry.focus_set()

        def do_create() -> None:
            name = var.get().strip() or "新题库"
            create_tree(name)
            self.tree_data = load_tree()
            self._undo_snapshot = None
            self.btn_undo.configure(state=tk.DISABLED)
            self.search_var.set("")
            self._filter_query = ""
            self._reload_tree()
            self._reload_tree_switcher()
            self._update_stats()
            self.status.set(f"已新建题库：{name}")
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, padx=16, pady=14)
        ttk.Button(btns, text="创建", command=do_create).pack(side=tk.LEFT)
        ttk.Button(btns, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=8)
        entry.bind("<Return>", lambda _e: do_create())

    def on_rename_tree(self) -> None:
        entry_info = self._current_tree_entry()
        dialog = tk.Toplevel(self)
        dialog.title("重命名题库")
        dialog.geometry("480x180")
        dialog.transient(self)
        ttk.Label(dialog, text="新标题：", font=self.font_ui).pack(padx=16, pady=(20, 6))
        var = tk.StringVar(value=entry_info.get("title") or "")
        entry = tk.Entry(dialog, textvariable=var, font=self.font_input)
        entry.pack(fill=tk.X, padx=16)
        entry.focus_set()

        def do_rename() -> None:
            name = var.get().strip()
            if not name:
                return
            rename_tree(current_tree_id(), name)
            self._reload_tree_switcher()
            self.status.set(f"已重命名为：{name}")
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, padx=16, pady=14)
        ttk.Button(btns, text="确定", command=do_rename).pack(side=tk.LEFT)
        ttk.Button(btns, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=8)
        entry.bind("<Return>", lambda _e: do_rename())

    def on_delete_tree(self) -> None:
        entry_info = self._current_tree_entry()
        name = entry_info.get("title") or "当前题库"
        if not messagebox.askyesno(
            "确认删除",
            f"删除题库「{name}」及其全部题目？\n（会同时删除对应文件，无法恢复）",
        ):
            return
        try:
            delete_tree(current_tree_id())
        except ValueError as e:
            messagebox.showwarning("无法删除", str(e))
            return
        self.tree_data = load_tree()
        self._undo_snapshot = None
        self.btn_undo.configure(state=tk.DISABLED)
        self.search_var.set("")
        self._filter_query = ""
        self._reload_tree()
        self._reload_tree_switcher()
        self._update_stats()
        self.status.set(f"已删除题库：{name}")

    def on_search_change(self, _event: object | None = None) -> None:
        self._filter_query = self.search_var.get().strip()
        self._reload_tree()

    def _focus_search(self) -> None:
        entry = getattr(self, "search_entry", None)
        if entry is not None:
            entry.focus_set()
            entry.select_range(0, tk.END)

    def _update_stats(self) -> None:
        s = tree_stats(self.tree_data)
        self.stats_var.set(f"共 {s['total']} 题 · 一级 {s['roots']} · 标签 {s['tags']}")

    # ----- 弹窗 / 朗读 / 重点 -----
    def _open_detail(
        self,
        title: str,
        text: str,
        font: tkfont.Font | None = None,
        *,
        answer_tools: bool = False,
    ) -> None:
        kwargs: dict[str, Any] = {}
        if answer_tools:
            kwargs["on_ai_query"] = self.on_ai_explain_answer
            kwargs["on_ai_metaphor"] = self.on_ai_metaphor_answer
        DetailPopup(self, title, text, font or self.font_body, **kwargs)

    def _bind_double_open(self, widget: tk.Misc, title: str) -> None:
        def _h(_event: object) -> str:
            text = widget.get("1.0", "end-1c")  # type: ignore[attr-defined]
            self._open_detail(title, text)
            return "break"

        widget.bind("<Double-Button-1>", _h)

    def on_key_points(self) -> None:
        text = self.a_edit.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("查看重点", "当前节点没有答案")
            return
        points = extract_key_points(text)
        if not points:
            messagebox.showinfo("查看重点", "未能提取出重点（答案过短）")
            return
        rendered = "\n".join(f"• {p}" for p in points)
        self._open_detail("参考答案 · 重点", rendered, self.font_body, answer_tools=True)

    def on_ai_explain_answer(self, answer: str | None = None) -> None:
        self._ai_answer_assist(
            mode="explain",
            answer=answer,
            status="正在用 AI 解释答案…",
            title_prefix="AI 查询 · 答案解释",
        )

    def on_ai_metaphor_answer(self, answer: str | None = None) -> None:
        self._ai_answer_assist(
            mode="metaphor",
            answer=answer,
            status="正在用 AI 生成比喻…",
            title_prefix="AI 比喻 · 通俗讲解",
        )

    def _ai_answer_assist(
        self,
        *,
        mode: str,
        answer: str | None,
        status: str,
        title_prefix: str,
    ) -> None:
        ans = (answer if answer is not None else self.a_edit.get("1.0", "end-1c")).strip()
        if not ans:
            messagebox.showinfo("提示", "当前没有可解释的参考答案")
            return
        question = self.q_edit.get("1.0", "end-1c").strip()
        self._persist_cfg()
        self.status.set(status)

        if mode == "metaphor":
            system = (
                "你是面试教练。用 1~2 个生动比喻解释候选人答案，"
                "每个比喻后用 2~3 句对应回技术要点；口语化、便于背诵；中文作答。"
            )
            user = (
                f"面试问题：\n{question or '（未提供）'}\n\n"
                f"参考答案：\n{ans}\n\n"
                "请输出：比喻讲解 + 对应技术要点 + 一句口述开场白。"
            )
        else:
            system = (
                "你是资深面试官教练。解释这段参考答案：关键点、为什么这样答、"
                "追问风险与更好的口述结构；条理清晰；中文作答。"
            )
            user = (
                f"面试问题：\n{question or '（未提供）'}\n\n"
                f"参考答案：\n{ans}\n\n"
                "请输出：① 核心结论 ② 要点拆解 ③ 常见踩坑 ④ 30 秒口述版。"
            )

        def job() -> str:
            return chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=90,
                max_tokens=1600,
            )

        def ok(text: str) -> None:
            self._open_detail(title_prefix, text or "（空响应）", answer_tools=True)
            self.status.set(f"{title_prefix} 完成")

        self._run_bg(job, ok)

    def on_speak(self) -> None:
        text = self.a_edit.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("朗读", "当前节点没有答案可朗读")
            return
        if self._speaking:
            messagebox.showinfo("朗读", "正在朗读中，请稍候")
            return
        self._speaking = True
        self.status.set("正在朗读…")

        def worker() -> None:
            try:
                _tts_speak(text)
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda m=str(e): self._speak_done(False, m))
                return
            self.after(0, lambda: self._speak_done(True, ""))

        threading.Thread(target=worker, daemon=True).start()

    def _speak_done(self, ok: bool, msg: str) -> None:
        self._speaking = False
        if ok:
            self.status.set("朗读完成")
        else:
            self.status.set("朗读失败")
            messagebox.showerror("朗读失败", msg)

    # ----- 划词查询（AI / 浏览器） -----
    def _setup_answer_lookup(self, widget: tk.Text) -> None:
        def on_double(event: tk.Event) -> str:  # type: ignore[type-arg]
            term = ""
            try:
                term = widget.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            except tk.TclError:
                pass
            if not term:
                idx = widget.index(f"@{event.x},{event.y}")
                term = expand_term_at(widget, idx)
            if term:
                self._choose_lookup(term)
            return "break"

        def on_right(event: tk.Event) -> str:  # type: ignore[type-arg]
            term = ""
            try:
                term = widget.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            except tk.TclError:
                pass
            if not term:
                idx = widget.index(f"@{event.x},{event.y}")
                term = expand_term_at(widget, idx)
            menu = tk.Menu(widget, tearoff=0)
            if term:
                menu.add_command(
                    label=f"AI 查询「{term[:20]}」",
                    command=lambda t=term: self._run_lookup(t, "ai"),
                )
                menu.add_command(
                    label=f"浏览器查询「{term[:20]}」",
                    command=lambda t=term: self._run_lookup(t, "browser"),
                )
                menu.add_separator()
            menu.add_command(
                label="弹窗打开全文",
                command=lambda: self._open_detail(
                    "参考答案", widget.get("1.0", "end-1c"), answer_tools=True
                ),
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"

        widget.bind("<Double-Button-1>", on_double)
        widget.bind("<Button-3>", on_right)

    def _term_tag(self, term: str) -> str:
        import hashlib

        return "lt_" + hashlib.md5(term.encode("utf-8")).hexdigest()[:12]

    def _current_selection_term(self) -> str:
        try:
            return self.a_edit.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except tk.TclError:
            return ""

    def on_lookup_selection(self) -> None:
        term = self._current_selection_term()
        if not term:
            messagebox.showinfo(
                "划词查询",
                "请先在答案里划选要查的名词/术语，或双击某个词。",
            )
            return
        self._choose_lookup(term)

    def _choose_lookup(self, term: str) -> None:
        term = (term or "").strip()
        if not term:
            return
        if len(term) > 80:
            messagebox.showinfo("划词查询", "选区过长，请只选一个词或短语（建议 ≤80 字）")
            return
        LookupChooser(
            self,
            term,
            on_ai=lambda: self._run_lookup(term, "ai"),
            on_browser=lambda: self._run_lookup(term, "browser"),
            font=self.font_ui,
        )

    def _run_lookup(self, term: str, mode: str) -> None:
        term = term.strip()
        if not term:
            return
        self.status.set(f"正在查询「{term}」…")
        self._persist_cfg()

        def job() -> tuple[str, str]:
            if mode == "ai":
                content = chat(
                    api_key=self.cfg["api_key"],
                    base_url=self.cfg["base_url"],
                    model=self.cfg["model"],
                    messages=[
                        {
                            "role": "system",
                            "content": "你是技术名词解释助手。用简洁中文解释术语，先一句结论，再给 2~4 条要点，不要废话。",
                        },
                        {
                            "role": "user",
                            "content": f"请解释这个词/短语（面试语境）：{term}",
                        },
                    ],
                    timeout=60,
                    max_tokens=800,
                )
                return mode, content
            text = lookup_browser(term)
            return mode, text

        def ok(pair: tuple[str, str]) -> None:
            m, text = pair
            if m == "browser":
                self._term_cache[term] = text
            elif term not in self._term_cache:
                self._prefetch_browser_tip(term)
            self._highlight_term(term)
            title = f"查询「{term}」· {'AI' if m == 'ai' else '浏览器'}"
            self._open_detail(title, text)
            self.status.set(f"已完成查询：{term}")

        self._run_bg(job, ok)

    def _prefetch_browser_tip(self, term: str) -> None:
        if term in self._term_cache or term in self._hover_fetching:
            return
        self._hover_fetching.add(term)

        def worker() -> None:
            try:
                text = lookup_browser(term)
            except Exception:
                self.after(0, lambda: self._hover_fetching.discard(term))
                return
            self.after(0, lambda: self._cache_browser(term, text))

        threading.Thread(target=worker, daemon=True).start()

    def _cache_browser(self, term: str, text: str) -> None:
        self._term_cache[term] = text
        self._hover_fetching.discard(term)
        self._highlight_term(term)

    def _highlight_term(self, term: str) -> None:
        if not term:
            return
        tag = self._term_tag(term)
        self.a_edit.tag_configure(tag, foreground="#0b5cad", underline=True)
        self.a_edit.tag_remove(tag, "1.0", tk.END)
        start = "1.0"
        while True:
            pos = self.a_edit.search(term, start, stopindex=tk.END)
            if not pos:
                break
            end = f"{pos}+{len(term)}c"
            self.a_edit.tag_add(tag, pos, end)
            start = end
        self.a_edit.tag_bind(tag, "<Enter>", lambda e, t=term: self._on_term_enter(e, t))
        self.a_edit.tag_bind(tag, "<Leave>", lambda _e: self._hide_term_tip())

    def _reapply_term_highlights(self) -> None:
        body = self.a_edit.get("1.0", "end-1c")
        for term in list(self._term_cache.keys()):
            if term and term in body:
                self._highlight_term(term)

    def _on_term_enter(self, event: tk.Event, term: str) -> None:  # type: ignore[type-arg]
        tip = self._term_cache.get(term)
        if tip:
            self._show_term_tip(event, tip)
            return
        self._show_term_tip(event, f"正在从浏览器查询「{term}」…")
        self._prefetch_browser_tip(term)

        def poll(n: int = 0) -> None:
            if term in self._term_cache:
                self._show_term_tip(event, self._term_cache[term])
                return
            if n < 20:
                self.after(300, lambda: poll(n + 1))

        self.after(300, lambda: poll(0))

    def _show_term_tip(self, event: tk.Event, text: str) -> None:  # type: ignore[type-arg]
        self._hide_term_tip()
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        try:
            tip.attributes("-topmost", True)
        except tk.TclError:
            pass
        tip.geometry(f"+{event.x_root + 12}+{event.y_root + 16}")
        preview = (text or "").strip()
        if len(preview) > 420:
            preview = preview[:420] + "…"
        tk.Label(
            tip,
            text=preview,
            justify=tk.LEFT,
            background="#FFF8DC",
            foreground="#1a1a1a",
            relief=tk.SOLID,
            borderwidth=1,
            padx=10,
            pady=8,
            wraplength=480,
            font=self.font_tip,
        ).pack()
        self._term_tip_win = tip

    def _hide_term_tip(self) -> None:
        if self._term_tip_win is not None:
            try:
                self._term_tip_win.destroy()
            except tk.TclError:
                pass
            self._term_tip_win = None

    # ----- 复制 / 刷题 / 撤销 / 导出 -----
    def _selected_node(self) -> dict[str, Any] | None:
        node_id = self._selected_node_id()
        if not node_id:
            return None
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        return node

    def on_copy_answer(self) -> None:
        node = self._selected_node()
        if node is None:
            messagebox.showinfo("提示", "请先选中一个节点")
            return
        self.clipboard_clear()
        self.clipboard_append(node.get("answer") or "")
        self.status.set("已复制答案到剪贴板")

    def on_copy_qa(self) -> None:
        node = self._selected_node()
        if node is None:
            messagebox.showinfo("提示", "请先选中一个节点")
            return
        text = f"Q：{node.get('question') or ''}\n\nA：{node.get('answer') or ''}"
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("已复制「问题+答案」到剪贴板")

    def on_quiz(self) -> None:
        QuizWindow(self, self.tree_data.get("nodes") or [], self.font_ui_bold, self.font_body, self.font_ui)

    def on_undo_refresh(self) -> None:
        if self._undo_snapshot is None:
            self.status.set("暂无可撤销的刷新")
            return
        if not messagebox.askyesno("撤销刷新", "回滚到上一次刷新前的状态？当前新增/补充会丢失。"):
            return
        self.tree_data = deepcopy(self._undo_snapshot)
        self._undo_snapshot = None
        self.btn_undo.configure(state=tk.DISABLED)
        self._save_current_tree()
        self._reload_tree()
        self._update_stats()
        self.status.set("已撤销上次刷新")

    def on_export_html(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html")],
            initialfile="interview_tree.html",
        )
        if not path:
            return
        Path(path).write_text(export_html(self.tree_data), encoding="utf-8")
        messagebox.showinfo("导出完成", path)

    def on_export_pdf(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="interview_tree.pdf",
        )
        if not path:
            return
        try:
            export_pdf(self.tree_data, path)
        except ImportError:
            messagebox.showerror(
                "缺少依赖",
                "未安装 reportlab，请在 interview-tree-desktop 目录执行：\npip install -r requirements.txt",
            )
            return
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("导出失败", str(e))
            return
        messagebox.showinfo("导出完成", path)

    # ----- 后台任务进度 -----
    def _start_ticker(self) -> None:
        self._task_start = time.monotonic()
        self._stop_ticker()
        self._ticker_id = self.after(1000, self._tick)

    def _tick(self) -> None:
        if not self._busy:
            return
        elapsed = int(time.monotonic() - self._task_start)
        self.status.set(f"正在请求 DeepSeek… 已等待 {elapsed}s")
        self._ticker_id = self.after(1000, self._tick)

    def _stop_ticker(self) -> None:
        if self._ticker_id is not None:
            try:
                self.after_cancel(self._ticker_id)
            except tk.TclError:
                pass
            self._ticker_id = None

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for b in (
            self.btn_generate,
            self.btn_offline,
            self.btn_expand,
            self.btn_sync,
            self.btn_refresh,
            self.btn_coding,
            self.btn_undo,
            self.btn_save,
            self.btn_export,
            self.btn_export_html,
            self.btn_export_pdf,
        ):
            b.configure(state=state)
        self.tree_combo.configure(state=tk.DISABLED if busy else "readonly")

    def _run_bg(self, fn: Callable[[], Any], on_ok: Callable[[Any], None]) -> None:
        if self._busy:
            messagebox.showinfo("请稍候", "已有任务在进行中")
            return
        self._set_busy(True)
        self._persist_cfg()
        self._start_ticker()

        def worker() -> None:
            try:
                result = fn()
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                self.after(0, lambda m=msg: self._fail(m))
                return
            self.after(0, lambda r=result: self._ok(r, on_ok))

        threading.Thread(target=worker, daemon=True).start()

    def _ok(self, result: Any, on_ok: Callable[[Any], None]) -> None:
        self._stop_ticker()
        self._set_busy(False)
        try:
            on_ok(result)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("处理失败", str(e))

    def _fail(self, msg: str) -> None:
        self._stop_ticker()
        self._set_busy(False)
        self.status.set("失败")
        messagebox.showerror("DeepSeek / 任务失败", msg)

    def _selected_node_id(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self._iid_to_id.get(sel[0])

    def _reload_tree(self, select_id: str | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        self._iid_to_id.clear()
        self._id_to_iid.clear()
        title = self.tree_data.get("title") or "面试题树"
        self.title(f"FRAME 面试题树 · DeepSeek — {title}")

        source = filter_tree(self.tree_data, self._filter_query).get("nodes") or []

        def add(parent_iid: str, nodes: list[dict[str, Any]]) -> None:
            for n in nodes:
                iid = self.tree.insert(
                    parent_iid,
                    "end",
                    text=(
                        ("[实操] " if n.get("kind") == "coding" else "")
                        + (n.get("question") or "")
                    ),
                    values=(", ".join(n.get("tags") or []), len(n.get("children") or [])),
                    open=parent_iid == "",
                )
                self._iid_to_id[iid] = n["id"]
                self._id_to_iid[n["id"]] = iid
                add(iid, n.get("children") or [])

        add("", source)
        if select_id and select_id in self._id_to_iid:
            iid = self._id_to_iid[select_id]
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self.on_select()
        self._update_stats()

    def on_select(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        self.q_edit.delete("1.0", tk.END)
        self.q_edit.insert("1.0", node.get("question") or "")
        self.a_edit.delete("1.0", tk.END)
        self.a_edit.insert("1.0", node.get("answer") or "")
        self.tags_edit.delete(0, tk.END)
        self.tags_edit.insert(0, ", ".join(node.get("tags") or []))
        self._reapply_term_highlights()
        if node.get("kind") == "coding":
            self.status.set("实操题：点中间栏「实操实验室」写代码并跑自测")

    def on_apply(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            messagebox.showinfo("提示", "请先选中一个节点")
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        node["question"] = self.q_edit.get("1.0", "end-1c").strip() or node["question"]
        node["answer"] = self.a_edit.get("1.0", "end-1c").strip()
        node["tags"] = [t.strip() for t in self.tags_edit.get().split(",") if t.strip()]
        node["source"] = "manual"
        self._save_current_tree()
        self._reload_tree(select_id=node_id)
        self.status.set("已写回并保存")

    def on_delete(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            return
        node, parent, idx = find_node(self.tree_data.get("nodes") or [], node_id)
        if node is None or parent is None or idx < 0:
            return
        if not messagebox.askyesno("确认", "删除该节点及其全部子节点？"):
            return
        parent.pop(idx)
        self._save_current_tree()
        self._reload_tree()
        self.q_edit.delete("1.0", tk.END)
        self.a_edit.delete("1.0", tk.END)
        self.tags_edit.delete(0, tk.END)

    def on_save(self) -> None:
        self._persist_cfg()
        self._save_current_tree()
        messagebox.showinfo("已保存", f"配置与题树已写入：\n{tree_path()}")

    def on_export(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            initialfile="interview_tree.md",
        )
        if not path:
            return
        Path(path).write_text(export_markdown(self.tree_data), encoding="utf-8")
        messagebox.showinfo("导出完成", path)

    def on_offline_seed(self) -> None:
        jd = self.jd_edit.get("1.0", "end-1c").strip() or DEFAULT_JD
        self.tree_data = seed_offline_tree(jd)
        self._undo_snapshot = None
        self.btn_undo.configure(state=tk.DISABLED)
        self._save_current_tree()
        self._persist_cfg()
        self._reload_tree()
        self.status.set("已生成离线种子树（可再联网同步升级）")

    def on_test(self) -> None:
        self._persist_cfg()

        def job() -> str:
            return test_connection(
                self.cfg["api_key"], self.cfg["base_url"], self.cfg["model"]
            )

        def ok(text: str) -> None:
            messagebox.showinfo("连接成功", (text or "OK")[:300])
            self.status.set("DeepSeek 连接正常")

        self._run_bg(job, ok)

    def on_generate(self) -> None:
        jd = self.jd_edit.get("1.0", "end-1c").strip()
        if not jd:
            messagebox.showwarning("缺少 JD", "请先在左侧输入职位描述")
            return
        extra = self.extra_edit.get("1.0", "end-1c").strip()
        self._persist_cfg()
        self.status.set("正在请求 DeepSeek 生成题树…")

        def job() -> dict[str, Any]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_generate_messages(jd, extra),
            )
            return parse_generate_payload(content)

        def ok(data: dict[str, Any]) -> None:
            self.tree_data = normalize_tree(
                {"version": 1, "title": data["title"], "nodes": data["nodes"]}
            )
            self._undo_snapshot = None
            self.btn_undo.configure(state=tk.DISABLED)
            self._save_current_tree()
            self._reload_tree()
            self.status.set(
                f"已生成 {len(self.tree_data.get('nodes') or [])} 个一级题目并保存"
            )

        self._run_bg(job, ok)

    def on_generate_coding(self) -> None:
        jd = self.jd_edit.get("1.0", "end-1c").strip() or DEFAULT_JD
        extra = self.extra_edit.get("1.0", "end-1c").strip()
        self._persist_cfg()
        self.status.set("正在生成实操编程题…")

        def job() -> list[dict[str, Any]]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_coding_messages(jd, extra, count=3),
                timeout=180,
                max_tokens=4096,
            )
            return parse_coding_payload(content)

        def ok(raw_nodes: list[dict[str, Any]]) -> None:
            nodes = self.tree_data.setdefault("nodes", [])
            added = 0
            first_id = None
            for raw in raw_nodes:
                node = normalize_node({**raw, "kind": "coding", "source": "deepseek-coding"})
                nodes.append(node)
                added += 1
                if first_id is None:
                    first_id = node["id"]
            self._save_current_tree()
            self._reload_tree(select_id=first_id)
            self.status.set(f"已追加 {added} 道实操编程题（可点「实操实验室」开写）")

        self._run_bg(job, ok)

    def on_open_coding_lab(self) -> None:
        node = self._selected_node()
        if node is None or node.get("kind") != "coding":
            # 若未选中实操题，尝试打开第一道实操题
            coding_nodes = [n for n in walk(self.tree_data.get("nodes") or []) if n.get("kind") == "coding"]
            if not coding_nodes:
                messagebox.showinfo(
                    "实操实验室",
                    "题树里还没有实操题。可先点「离线种子树」或「⑤ 生成实操编程题」。",
                )
                return
            if node is None or node.get("kind") != "coding":
                node = coding_nodes[0]
                messagebox.showinfo(
                    "实操实验室",
                    f"未选中实操题，已打开：\n{node.get('question')}",
                )
        CodingLabWindow(self, node, self.font_ui, self.font_input)

    def on_refresh(self) -> None:
        jd = self.jd_edit.get("1.0", "end-1c").strip() or DEFAULT_JD
        extra = self.extra_edit.get("1.0", "end-1c").strip()
        outline = tree_outline(self.tree_data)
        self._persist_cfg()
        # 记录刷新前快照，便于撤销
        self._undo_snapshot = deepcopy(self.tree_data)
        self.btn_undo.configure(state=tk.NORMAL)
        self.status.set("正在刷新题树（追加/补充，不删除原文）…")

        def job() -> dict[str, Any]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_refresh_messages(jd, outline, extra),
                timeout=180,
                max_tokens=4096,
            )
            return parse_refresh_payload(content)

        def ok(payload: dict[str, Any]) -> None:
            stats = merge_refresh_into_tree(self.tree_data, payload)
            self._save_current_tree()
            self._reload_tree()
            self.status.set(
                f"刷新完成：新增 {stats['added']} · 补充答案 {stats['supplemented']} · 追加子题 {stats['child_added']}"
            )

        self._run_bg(job, ok)

    def on_expand(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            messagebox.showinfo("提示", "请先选中要生长的节点")
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        path = path_to_node(self.tree_data.get("nodes") or [], node_id) or []
        jd = self.jd_edit.get("1.0", "end-1c").strip() or DEFAULT_JD
        count = int(self.expand_count.get())
        self._persist_cfg()
        self.status.set("正在展开子题…")

        def job() -> list[dict[str, Any]]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_expand_messages(
                    jd, path, node["question"], node.get("answer") or "", count
                ),
            )
            return parse_expand_payload(content)

        def ok(children: list[dict[str, Any]]) -> None:
            attach_children(node, children)
            self._save_current_tree()
            self._reload_tree(select_id=node_id)
            self.status.set(f"已生长 {len(children)} 个子题")

        self._run_bg(job, ok)

    def on_sync(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            messagebox.showinfo("提示", "请先选中要同步的节点")
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        path = path_to_node(self.tree_data.get("nodes") or [], node_id) or []
        jd = self.jd_edit.get("1.0", "end-1c").strip() or DEFAULT_JD
        self._persist_cfg()
        self.status.set("正在与 DeepSeek 同步…")

        def job() -> dict[str, Any]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_sync_messages(
                    jd, path, node["question"], node.get("answer") or ""
                ),
            )
            return parse_sync_payload(content)

        def ok(patch: dict[str, Any]) -> None:
            replace_node_content(node, patch)
            self._save_current_tree()
            self._reload_tree(select_id=node_id)
            self.status.set("已与 DeepSeek 同步并保存到本地")

        self._run_bg(job, ok)


def main() -> int:
    enable_windows_dpi_awareness()
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
