# -*- coding: utf-8 -*-
"""FRAME 岗位面试题树 — DeepSeek 可生长桌面端（tkinter，无 Qt 依赖）。"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from defaults import DEFAULT_BASE_URL, DEFAULT_JD, DEFAULT_MODEL
from deepseek_client import chat, test_connection
from prompts import (
    build_expand_messages,
    build_generate_messages,
    build_sync_messages,
    parse_expand_payload,
    parse_generate_payload,
    parse_sync_payload,
)
from tree_store import (
    attach_children,
    export_markdown,
    find_node,
    load_config,
    load_tree,
    normalize_tree,
    path_to_node,
    replace_node_content,
    save_config,
    save_tree,
    seed_offline_tree,
    tree_path,
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


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FRAME 面试题树 · DeepSeek")
        self.geometry("1280x820")
        self.minsize(960, 640)
        try:
            self.tk.call("tk", "scaling", 1.25)
        except tk.TclError:
            pass

        self.tree_data = load_tree()
        self.cfg = load_config()
        if not self.cfg.get("jd_text"):
            self.cfg["jd_text"] = DEFAULT_JD

        self._busy = False
        self._iid_to_id: dict[str, str] = {}
        self._id_to_iid: dict[str, str] = {}

        self._setup_fonts()
        self._build_ui()
        self._reload_tree()
        self.status.set(f"本地文件：{tree_path()}")

        if not (self.tree_data.get("nodes") or []):
            self.on_offline_seed()

    def _setup_fonts(self) -> None:
        family = pick_ui_font_family(self)
        self.font_ui = tkfont.Font(family=family, size=11)
        self.font_ui_bold = tkfont.Font(family=family, size=12, weight="bold")
        self.font_body = tkfont.Font(family=family, size=12)
        self.font_tree = tkfont.Font(family=family, size=11)
        self.font_status = tkfont.Font(family=family, size=10)

        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            try:
                style.theme_use("winnative")
            except tk.TclError:
                pass

        style.configure(".", font=self.font_ui)
        style.configure("TLabel", font=self.font_ui)
        style.configure("TButton", font=self.font_ui)
        style.configure("TEntry", font=self.font_ui)
        style.configure("TSpinbox", font=self.font_ui)
        style.configure("Treeview", font=self.font_tree, rowheight=28)
        style.configure("Treeview.Heading", font=self.font_ui_bold)
        style.configure("Title.TLabel", font=self.font_ui_bold)

    # ----- UI -----
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(paned, padding=8)
        mid = ttk.Frame(paned, padding=8)
        right = ttk.Frame(paned, padding=8)
        paned.add(left, weight=2)
        paned.add(mid, weight=3)
        paned.add(right, weight=2)

        # left: config + JD
        ttk.Label(left, text="DeepSeek 接入", style="Title.TLabel").pack(anchor="w")
        form = ttk.Frame(left)
        form.pack(fill=tk.X, pady=4)
        ttk.Label(form, text="API Key").grid(row=0, column=0, sticky="w")
        self.api_key = ttk.Entry(form, show="*")
        self.api_key.insert(0, self.cfg.get("api_key", ""))
        self.api_key.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(form, text="Base URL").grid(row=1, column=0, sticky="w")
        self.base_url = ttk.Entry(form)
        self.base_url.insert(0, self.cfg.get("base_url") or DEFAULT_BASE_URL)
        self.base_url.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Label(form, text="Model").grid(row=2, column=0, sticky="w")
        self.model = ttk.Entry(form)
        self.model.insert(0, self.cfg.get("model") or DEFAULT_MODEL)
        self.model.grid(row=2, column=1, sticky="ew", pady=2)
        form.columnconfigure(1, weight=1)
        ttk.Button(left, text="测试连接", command=self.on_test).pack(anchor="w", pady=4)

        ttk.Label(left, text="职位描述（可编辑后解析）", style="Title.TLabel").pack(
            anchor="w", pady=(10, 2)
        )
        self.jd_edit = tk.Text(left, height=14, wrap=tk.WORD, font=self.font_body, undo=True)
        self.jd_edit.insert("1.0", self.cfg.get("jd_text") or DEFAULT_JD)
        self.jd_edit.pack(fill=tk.BOTH, expand=True)

        ttk.Label(left, text="生成补充说明（可选）").pack(anchor="w", pady=(8, 2))
        self.extra_edit = tk.Text(left, height=3, wrap=tk.WORD, font=self.font_body, undo=True)
        self.extra_edit.pack(fill=tk.X)

        row = ttk.Frame(left)
        row.pack(fill=tk.X, pady=6)
        ttk.Label(row, text="每次展开子题数").pack(side=tk.LEFT)
        self.expand_count = tk.IntVar(value=3)
        ttk.Spinbox(row, from_=1, to=6, textvariable=self.expand_count, width=5).pack(
            side=tk.LEFT, padx=6
        )

        self.btn_generate = ttk.Button(left, text="① 解析 JD 并生成题树", command=self.on_generate)
        self.btn_generate.pack(fill=tk.X, pady=2)
        self.btn_offline = ttk.Button(left, text="离线种子树", command=self.on_offline_seed)
        self.btn_offline.pack(fill=tk.X, pady=2)
        self.btn_expand = ttk.Button(left, text="② 展开选中节点（生长）", command=self.on_expand)
        self.btn_expand.pack(fill=tk.X, pady=2)
        self.btn_sync = ttk.Button(left, text="③ 联网同步选中节点", command=self.on_sync)
        self.btn_sync.pack(fill=tk.X, pady=2)

        row2 = ttk.Frame(left)
        row2.pack(fill=tk.X, pady=6)
        self.btn_save = ttk.Button(row2, text="保存到本地", command=self.on_save)
        self.btn_save.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        self.btn_export = ttk.Button(row2, text="导出 Markdown", command=self.on_export)
        self.btn_export.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # mid: tree
        ttk.Label(
            mid, text="面试题树（点选后右侧可编辑，可向下生长）", style="Title.TLabel"
        ).pack(anchor="w")
        tree_wrap = ttk.Frame(mid)
        tree_wrap.pack(fill=tk.BOTH, expand=True, pady=4)
        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("tags", "kids"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="问题")
        self.tree.heading("tags", text="标签")
        self.tree.heading("kids", text="子节点")
        self.tree.column("#0", width=420, stretch=True)
        self.tree.column("tags", width=140, stretch=False)
        self.tree.column("kids", width=60, stretch=False, anchor="center")
        ysb = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.on_select())

        # right: editor
        ttk.Label(right, text="当前节点", style="Title.TLabel").pack(anchor="w")
        ttk.Label(right, text="问题").pack(anchor="w")
        self.q_edit = tk.Text(right, height=4, wrap=tk.WORD, font=self.font_body, undo=True)
        self.q_edit.pack(fill=tk.X, pady=2)
        ttk.Label(right, text="参考答案").pack(anchor="w")
        self.a_edit = tk.Text(right, wrap=tk.WORD, font=self.font_body, undo=True)
        self.a_edit.pack(fill=tk.BOTH, expand=True, pady=2)
        ttk.Label(right, text="标签（逗号分隔）").pack(anchor="w")
        self.tags_edit = ttk.Entry(right)
        self.tags_edit.pack(fill=tk.X, pady=2)
        ttk.Button(right, text="写回当前节点（本地）", command=self.on_apply).pack(
            fill=tk.X, pady=4
        )
        ttk.Button(right, text="删除当前节点", command=self.on_delete).pack(fill=tk.X)

        self.status = tk.StringVar(value="ready")
        ttk.Label(self, textvariable=self.status, anchor="w", font=self.font_status).grid(
            row=1, column=0, sticky="ew", padx=8, pady=4
        )

    # ----- helpers -----
    def _persist_cfg(self) -> None:
        self.cfg = {
            "api_key": self.api_key.get().strip(),
            "base_url": self.base_url.get().strip() or DEFAULT_BASE_URL,
            "model": self.model.get().strip() or DEFAULT_MODEL,
            "jd_text": self.jd_edit.get("1.0", "end-1c"),
        }
        save_config(self.cfg)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for b in (
            self.btn_generate,
            self.btn_offline,
            self.btn_expand,
            self.btn_sync,
            self.btn_save,
            self.btn_export,
        ):
            b.configure(state=state)

    def _run_bg(self, fn: Callable[[], Any], on_ok: Callable[[Any], None]) -> None:
        if self._busy:
            messagebox.showinfo("请稍候", "已有任务在进行中")
            return
        self._set_busy(True)
        self._persist_cfg()

        def worker() -> None:
            try:
                result = fn()
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self._fail(str(e)))
                return
            self.after(0, lambda: self._ok(result, on_ok))

        threading.Thread(target=worker, daemon=True).start()

    def _ok(self, result: Any, on_ok: Callable[[Any], None]) -> None:
        self._set_busy(False)
        try:
            on_ok(result)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("处理失败", str(e))

    def _fail(self, msg: str) -> None:
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

        def add(parent_iid: str, nodes: list[dict[str, Any]]) -> None:
            for n in nodes:
                iid = self.tree.insert(
                    parent_iid,
                    "end",
                    text=n.get("question") or "",
                    values=(", ".join(n.get("tags") or []), len(n.get("children") or [])),
                    open=parent_iid == "",
                )
                self._iid_to_id[iid] = n["id"]
                self._id_to_iid[n["id"]] = iid
                add(iid, n.get("children") or [])

        add("", self.tree_data.get("nodes") or [])
        if select_id and select_id in self._id_to_iid:
            iid = self._id_to_iid[select_id]
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self.on_select()

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
        save_tree(self.tree_data)
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
        save_tree(self.tree_data)
        self._reload_tree()
        self.q_edit.delete("1.0", tk.END)
        self.a_edit.delete("1.0", tk.END)
        self.tags_edit.delete(0, tk.END)

    def on_save(self) -> None:
        self._persist_cfg()
        save_tree(self.tree_data)
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
        save_tree(self.tree_data)
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
            save_tree(self.tree_data)
            self._reload_tree()
            self.status.set(
                f"已生成 {len(self.tree_data.get('nodes') or [])} 个一级题目并保存"
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
            save_tree(self.tree_data)
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
            save_tree(self.tree_data)
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
