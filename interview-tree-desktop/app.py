# -*- coding: utf-8 -*-
"""FRAME 岗位面试题树 — DeepSeek 可生长桌面端。"""

from __future__ import annotations

import sys
import traceback
from typing import Any, Callable

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QFormLayout,
    QSpinBox,
    QGroupBox,
)

from defaults import DEFAULT_BASE_URL, DEFAULT_JD, DEFAULT_MODEL
from deepseek_client import DeepSeekError, chat, test_connection
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
    path_to_node,
    replace_node_content,
    save_config,
    save_tree,
    seed_offline_tree,
    tree_path,
)


class Worker(QThread):
    finished_ok = Signal(object)
    finished_err = Signal(str)
    progress = Signal(str)

    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            self.finished_ok.emit(self._fn())
        except Exception as e:  # noqa: BLE001 — surface to UI
            self.finished_err.emit(f"{e}\n\n{traceback.format_exc(limit=4)}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FRAME 面试题树 · DeepSeek")
        self.resize(1280, 820)

        self.tree_data = load_tree()
        self.cfg = load_config()
        if not self.cfg.get("jd_text"):
            self.cfg["jd_text"] = DEFAULT_JD

        self._worker: Worker | None = None
        self._item_by_id: dict[str, QTreeWidgetItem] = {}

        self._build_ui()
        self._reload_tree_widget()
        self.statusBar().showMessage(f"本地文件：{tree_path()}")

    # ----- UI -----
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left = QWidget()
        left_l = QVBoxLayout(left)

        cfg_box = QGroupBox("DeepSeek 接入")
        form = QFormLayout(cfg_box)
        self.api_key = QLineEdit(self.cfg.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-...")
        self.base_url = QLineEdit(self.cfg.get("base_url") or DEFAULT_BASE_URL)
        self.model = QLineEdit(self.cfg.get("model") or DEFAULT_MODEL)
        form.addRow("API Key", self.api_key)
        form.addRow("Base URL", self.base_url)
        form.addRow("Model", self.model)
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self.on_test_connection)
        form.addRow("", test_btn)
        left_l.addWidget(cfg_box)

        jd_box = QGroupBox("职位描述（可编辑后解析）")
        jd_l = QVBoxLayout(jd_box)
        self.jd_edit = QPlainTextEdit(self.cfg.get("jd_text") or DEFAULT_JD)
        self.jd_edit.setPlaceholderText("粘贴 JD…")
        jd_l.addWidget(self.jd_edit)
        left_l.addWidget(jd_box, stretch=1)

        extra_box = QGroupBox("生成补充说明（可选）")
        extra_l = QVBoxLayout(extra_box)
        self.extra_edit = QPlainTextEdit()
        self.extra_edit.setPlaceholderText("例如：更偏 NestJS 与 SQL；答案控制在 2 分钟口述量")
        self.extra_edit.setFixedHeight(70)
        extra_l.addWidget(self.extra_edit)
        left_l.addWidget(extra_box)

        expand_row = QHBoxLayout()
        expand_row.addWidget(QLabel("每次展开子题数"))
        self.expand_count = QSpinBox()
        self.expand_count.setRange(1, 6)
        self.expand_count.setValue(3)
        expand_row.addWidget(self.expand_count)
        expand_row.addStretch(1)
        left_l.addLayout(expand_row)

        btn_row1 = QHBoxLayout()
        self.btn_generate = QPushButton("① 解析 JD 并生成题树")
        self.btn_generate.clicked.connect(self.on_generate)
        self.btn_offline = QPushButton("离线种子树")
        self.btn_offline.clicked.connect(self.on_offline_seed)
        btn_row1.addWidget(self.btn_generate)
        btn_row1.addWidget(self.btn_offline)
        left_l.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.btn_expand = QPushButton("② 展开选中节点（生长）")
        self.btn_expand.clicked.connect(self.on_expand)
        self.btn_sync = QPushButton("③ 联网同步选中节点")
        self.btn_sync.clicked.connect(self.on_sync)
        btn_row2.addWidget(self.btn_expand)
        btn_row2.addWidget(self.btn_sync)
        left_l.addLayout(btn_row2)

        btn_row3 = QHBoxLayout()
        self.btn_save = QPushButton("保存到本地")
        self.btn_save.clicked.connect(self.on_save)
        self.btn_export = QPushButton("导出 Markdown")
        self.btn_export.clicked.connect(self.on_export)
        btn_row3.addWidget(self.btn_save)
        btn_row3.addWidget(self.btn_export)
        left_l.addLayout(btn_row3)

        splitter.addWidget(left)

        mid = QWidget()
        mid_l = QVBoxLayout(mid)
        mid_l.addWidget(QLabel("面试题树（点击节点编辑右侧答案；可不断向下生长）"))
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["问题", "标签", "子节点"])
        self.tree_widget.itemSelectionChanged.connect(self.on_select)
        self.tree_widget.setColumnWidth(0, 420)
        mid_l.addWidget(self.tree_widget)
        splitter.addWidget(mid)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.addWidget(QLabel("当前节点"))
        self.q_edit = QPlainTextEdit()
        self.q_edit.setFixedHeight(90)
        right_l.addWidget(QLabel("问题"))
        right_l.addWidget(self.q_edit)
        right_l.addWidget(QLabel("参考答案"))
        self.a_edit = QPlainTextEdit()
        right_l.addWidget(self.a_edit, stretch=1)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("标签，逗号分隔")
        right_l.addWidget(self.tags_edit)
        apply_btn = QPushButton("写回当前节点（本地）")
        apply_btn.clicked.connect(self.on_apply_node)
        right_l.addWidget(apply_btn)
        del_btn = QPushButton("删除当前节点")
        del_btn.clicked.connect(self.on_delete_node)
        right_l.addWidget(del_btn)
        splitter.addWidget(right)

        splitter.setSizes([360, 560, 360])
        self.setStatusBar(QStatusBar())

        # menu
        act_reload = QAction("重新加载本地树", self)
        act_reload.triggered.connect(self.on_reload)
        self.menuBar().addAction(act_reload)

    # ----- helpers -----
    def _persist_cfg(self) -> None:
        self.cfg = {
            "api_key": self.api_key.text().strip(),
            "base_url": self.base_url.text().strip() or DEFAULT_BASE_URL,
            "model": self.model.text().strip() or DEFAULT_MODEL,
            "jd_text": self.jd_edit.toPlainText(),
        }
        save_config(self.cfg)

    def _set_busy(self, busy: bool) -> None:
        for w in (
            self.btn_generate,
            self.btn_expand,
            self.btn_sync,
            self.btn_offline,
            self.btn_save,
            self.btn_export,
        ):
            w.setEnabled(not busy)

    def _run_worker(self, fn: Callable[[], Any], on_ok: Callable[[Any], None]) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "请稍候", "已有任务在进行中")
            return
        self._set_busy(True)
        self._persist_cfg()

        worker = Worker(fn)
        self._worker = worker
        worker.progress.connect(lambda m: self.statusBar().showMessage(m))
        worker.finished_ok.connect(lambda result: self._on_worker_ok(result, on_ok))
        worker.finished_err.connect(self._on_worker_err)
        worker.start()

    def _on_worker_ok(self, result: Any, on_ok: Callable[[Any], None]) -> None:
        self._set_busy(False)
        try:
            on_ok(result)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "处理失败", str(e))

    def _on_worker_err(self, msg: str) -> None:
        self._set_busy(False)
        QMessageBox.critical(self, "DeepSeek / 任务失败", msg)
        self.statusBar().showMessage("失败")

    def _selected_node_id(self) -> str | None:
        items = self.tree_widget.selectedItems()
        if not items:
            return None
        return items[0].data(0, Qt.ItemDataRole.UserRole)

    def _reload_tree_widget(self, select_id: str | None = None) -> None:
        self.tree_widget.clear()
        self._item_by_id.clear()
        title = self.tree_data.get("title") or "面试题树"
        self.setWindowTitle(f"FRAME 面试题树 · DeepSeek — {title}")

        def add_items(parent: QTreeWidgetItem | None, nodes: list[dict[str, Any]]) -> None:
            for n in nodes:
                item = QTreeWidgetItem(
                    [
                        n.get("question") or "",
                        ", ".join(n.get("tags") or []),
                        str(len(n.get("children") or [])),
                    ]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, n["id"])
                self._item_by_id[n["id"]] = item
                if parent is None:
                    self.tree_widget.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                add_items(item, n.get("children") or [])

        add_items(None, self.tree_data.get("nodes") or [])
        self.tree_widget.expandToDepth(1)
        if select_id and select_id in self._item_by_id:
            item = self._item_by_id[select_id]
            self.tree_widget.setCurrentItem(item)
            item.setExpanded(True)

    def on_select(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        self.q_edit.setPlainText(node.get("question") or "")
        self.a_edit.setPlainText(node.get("answer") or "")
        self.tags_edit.setText(", ".join(node.get("tags") or []))

    def on_apply_node(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            QMessageBox.information(self, "提示", "请先选中一个节点")
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        node["question"] = self.q_edit.toPlainText().strip() or node["question"]
        node["answer"] = self.a_edit.toPlainText().strip()
        node["tags"] = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        node["source"] = "manual"
        save_tree(self.tree_data)
        self._reload_tree_widget(select_id=node_id)
        self.statusBar().showMessage("已写回并保存")

    def on_delete_node(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            return
        node, parent, idx = find_node(self.tree_data.get("nodes") or [], node_id)
        if node is None or parent is None or idx < 0:
            return
        if (
            QMessageBox.question(self, "确认", "删除该节点及其全部子节点？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        parent.pop(idx)
        save_tree(self.tree_data)
        self._reload_tree_widget()
        self.q_edit.clear()
        self.a_edit.clear()
        self.tags_edit.clear()

    def on_save(self) -> None:
        self._persist_cfg()
        save_tree(self.tree_data)
        QMessageBox.information(self, "已保存", f"配置与题树已写入：\n{tree_path()}")

    def on_reload(self) -> None:
        self.tree_data = load_tree()
        self._reload_tree_widget()
        self.statusBar().showMessage("已从本地重新加载")

    def on_export(self) -> None:
        from pathlib import Path

        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Markdown", "interview_tree.md", "Markdown (*.md)"
        )
        if not path:
            return
        Path(path).write_text(export_markdown(self.tree_data), encoding="utf-8")
        QMessageBox.information(self, "导出完成", path)

    def on_offline_seed(self) -> None:
        jd = self.jd_edit.toPlainText().strip() or DEFAULT_JD
        self.tree_data = seed_offline_tree(jd)
        save_tree(self.tree_data)
        self._persist_cfg()
        self._reload_tree_widget()
        self.statusBar().showMessage("已生成离线种子树（可再联网同步升级）")

    def on_test_connection(self) -> None:
        self._persist_cfg()

        def job() -> str:
            return test_connection(
                self.cfg["api_key"], self.cfg["base_url"], self.cfg["model"]
            )

        def ok(text: str) -> None:
            QMessageBox.information(self, "连接成功", text[:300] or "OK")

        self._run_worker(job, ok)

    def on_generate(self) -> None:
        jd = self.jd_edit.toPlainText().strip()
        if not jd:
            QMessageBox.warning(self, "缺少 JD", "请先在左侧输入职位描述")
            return
        extra = self.extra_edit.toPlainText().strip()
        self._persist_cfg()

        def job() -> dict[str, Any]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_generate_messages(jd, extra),
                progress=lambda m: self._worker.progress.emit(m) if self._worker else None,
            )
            parsed = parse_generate_payload(content)
            return {
                "title": parsed["title"],
                "nodes": parsed["nodes"],
            }

        def ok(data: dict[str, Any]) -> None:
            from tree_store import normalize_tree

            self.tree_data = normalize_tree(
                {
                    "version": 1,
                    "title": data["title"],
                    "nodes": data["nodes"],
                }
            )
            save_tree(self.tree_data)
            self._reload_tree_widget()
            self.statusBar().showMessage(
                f"已生成 {len(self.tree_data.get('nodes') or [])} 个一级题目并保存"
            )

        self._run_worker(job, ok)

    def on_expand(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            QMessageBox.information(self, "提示", "请先选中要生长的节点")
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        path = path_to_node(self.tree_data.get("nodes") or [], node_id) or []
        jd = self.jd_edit.toPlainText().strip() or DEFAULT_JD
        count = self.expand_count.value()
        self._persist_cfg()

        def job() -> list[dict[str, Any]]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_expand_messages(
                    jd, path, node["question"], node.get("answer") or "", count
                ),
                progress=lambda m: self._worker.progress.emit(m) if self._worker else None,
            )
            return parse_expand_payload(content)

        def ok(children: list[dict[str, Any]]) -> None:
            attach_children(node, children)
            save_tree(self.tree_data)
            self._reload_tree_widget(select_id=node_id)
            self.statusBar().showMessage(f"已生长 {len(children)} 个子题")

        self._run_worker(job, ok)

    def on_sync(self) -> None:
        node_id = self._selected_node_id()
        if not node_id:
            QMessageBox.information(self, "提示", "请先选中要同步的节点")
            return
        node, _, _ = find_node(self.tree_data.get("nodes") or [], node_id)
        if not node:
            return
        path = path_to_node(self.tree_data.get("nodes") or [], node_id) or []
        jd = self.jd_edit.toPlainText().strip() or DEFAULT_JD
        self._persist_cfg()

        def job() -> dict[str, Any]:
            content = chat(
                api_key=self.cfg["api_key"],
                base_url=self.cfg["base_url"],
                model=self.cfg["model"],
                messages=build_sync_messages(
                    jd, path, node["question"], node.get("answer") or ""
                ),
                progress=lambda m: self._worker.progress.emit(m) if self._worker else None,
            )
            return parse_sync_payload(content)

        def ok(patch: dict[str, Any]) -> None:
            replace_node_content(node, patch)
            save_tree(self.tree_data)
            self._reload_tree_widget(select_id=node_id)
            self.on_select()
            self.statusBar().showMessage("已与 DeepSeek 同步并保存到本地")

        self._run_worker(job, ok)


def main() -> int:
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    win = MainWindow()
    win.show()
    # Auto-seed empty tree for first launch
    if not (win.tree_data.get("nodes") or []):
        win.on_offline_seed()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
