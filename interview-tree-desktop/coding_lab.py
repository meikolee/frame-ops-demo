# -*- coding: utf-8 -*-
"""本地实操：多语言小段运行 + 自测用例。"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# 展示名 → 内部 id
LANG_OPTIONS: list[tuple[str, str]] = [
    ("Python", "python"),
    ("JavaScript (Node)", "javascript"),
    ("TypeScript", "typescript"),
    ("Go", "go"),
    ("Java", "java"),
]

LANG_LABELS = {lid: label for label, lid in LANG_OPTIONS}

STARTERS: dict[str, str] = {
    "python": "# write your code\ndef solve():\n    pass\n\nif __name__ == '__main__':\n    print(solve())\n",
    "javascript": "// write your code\nfunction solve() {\n  // TODO\n}\n\nconsole.log(solve());\n",
    "typescript": "// write your code\nfunction solve(): unknown {\n  // TODO\n  return null;\n}\n\nconsole.log(solve());\n",
    "go": "package main\n\nimport \"fmt\"\n\nfunc solve() any {\n\t// TODO\n\treturn nil\n}\n\nfunc main() {\n\tfmt.Println(solve())\n}\n",
    "java": "public class Main {\n  static Object solve() {\n    // TODO\n    return null;\n  }\n  public static void main(String[] args) {\n    System.out.println(solve());\n  }\n}\n",
}


def coerce_tests(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            code = item.get("code") or item.get("assert") or item.get("test")
            if code and str(code).strip():
                out.append(str(code).strip())
    return out


def normalize_lang(lang: str | None) -> str:
    s = (lang or "python").strip().lower()
    aliases = {
        "py": "python",
        "js": "javascript",
        "node": "javascript",
        "ts": "typescript",
        "golang": "go",
    }
    s = aliases.get(s, s)
    if s not in LANG_LABELS:
        return "python"
    return s


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def runtime_status(lang: str) -> tuple[bool, str]:
    """返回 (可用?, 说明)。"""
    lang = normalize_lang(lang)
    if lang == "python":
        return True, sys.executable
    if lang == "javascript":
        p = which("node")
        return (bool(p), p or "未找到 node，请安装 Node.js 并加入 PATH")
    if lang == "typescript":
        if which("tsx"):
            return True, "tsx"
        if which("npx"):
            return True, "npx tsx"
        if which("ts-node"):
            return True, "ts-node"
        return False, "未找到 tsx / npx / ts-node，请安装 Node.js 后执行: npm i -g tsx"
    if lang == "go":
        p = which("go")
        return (bool(p), p or "未找到 go，请安装 Go 并加入 PATH")
    if lang == "java":
        javac, java = which("javac"), which("java")
        if javac and java:
            return True, f"{javac} + {java}"
        return False, "未找到 javac/java，请安装 JDK 并加入 PATH"
    return False, f"不支持的语言：{lang}"


def _run_cmd(
    cmd: list[str], cwd: Path, timeout: float, env: dict[str, str] | None = None
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            env=env,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
            "stderr": f"执行超时（>{timeout}s）\n"
            + (e.stderr if isinstance(e.stderr, str) else ""),
            "timed_out": True,
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"找不到可执行文件：{e}",
            "timed_out": False,
        }


def run_snippet(lang: str, code: str, timeout: float = 8.0) -> dict[str, Any]:
    """按语言执行代码片段。"""
    lang = normalize_lang(lang)
    ok, info = runtime_status(lang)
    if not ok:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": info,
            "timed_out": False,
            "language": lang,
        }

    code = code or ""
    with tempfile.TemporaryDirectory(prefix="frame_lab_") as td:
        root = Path(td)
        if lang == "python":
            path = root / "snippet.py"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd([sys.executable, str(path)], root, timeout)
        elif lang == "javascript":
            path = root / "snippet.js"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["node", str(path)], root, timeout)
        elif lang == "typescript":
            path = root / "snippet.ts"
            path.write_text(code, encoding="utf-8")
            if which("tsx"):
                cmd = ["tsx", str(path)]
            elif which("ts-node"):
                cmd = ["ts-node", str(path)]
            else:
                cmd = ["npx", "--yes", "tsx", str(path)]
            result = _run_cmd(cmd, root, max(timeout, 60.0))  # npx 首次可能较慢
        elif lang == "go":
            path = root / "main.go"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["go", "run", str(path)], root, timeout)
        elif lang == "java":
            # 要求 public class Main
            path = root / "Main.java"
            path.write_text(code, encoding="utf-8")
            c = _run_cmd(["javac", str(path)], root, timeout)
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd(["java", "-cp", str(root), "Main"], root, timeout)
        else:
            result = {
                "ok": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"不支持的语言：{lang}",
                "timed_out": False,
            }
        result["language"] = lang
        return result


# 兼容旧调用名
def run_python_snippet(code: str, timeout: float = 5.0) -> dict[str, Any]:
    return run_snippet("python", code, timeout=timeout)


def run_with_tests(
    user_code: str,
    tests: list[str],
    lang: str = "python",
    timeout: float = 8.0,
) -> dict[str, Any]:
    """拼接用户代码与测试片段后逐条运行。"""
    lang = normalize_lang(lang)
    tests = [t for t in tests if t.strip()]
    if not tests:
        result = run_snippet(lang, user_code, timeout=timeout)
        result["passed"] = 0
        result["failed"] = 0
        result["total"] = 0
        result["details"] = []
        return result

    details: list[dict[str, Any]] = []
    passed = failed = 0
    for i, test in enumerate(tests, start=1):
        harness = _wrap_test(lang, user_code or "", test)
        r = run_snippet(lang, harness, timeout=timeout)
        ok = bool(r.get("ok"))
        if ok:
            passed += 1
            msg = "通过"
        else:
            failed += 1
            err = (r.get("stderr") or r.get("stdout") or "失败").strip()
            msg = err.splitlines()[-1] if err else "失败"
        details.append({"index": i, "ok": ok, "test": test, "message": msg})

    return {
        "ok": failed == 0,
        "passed": passed,
        "failed": failed,
        "total": len(tests),
        "details": details,
        "stdout": "",
        "stderr": "",
        "returncode": 0 if failed == 0 else 1,
        "timed_out": False,
        "language": lang,
    }


def _wrap_test(lang: str, user_code: str, test: str) -> str:
    lang = normalize_lang(lang)
    if lang == "python":
        return user_code + "\n\n# --- auto test ---\n" + test + "\n"
    if lang == "javascript":
        return (
            user_code
            + "\n\nconst assert = require('assert');\n"
            + "// --- auto test ---\n"
            + test
            + "\n"
        )
    if lang == "typescript":
        return (
            user_code
            + "\n\nimport assert from 'assert';\n"
            + "// --- auto test ---\n"
            + test
            + "\n"
        )
    if lang == "go":
        # 测试片段应是可放在 main 里的语句；若用户已有 main，改为追加 Test 函数较难。
        # 约定：测试为可直接放在 package main 内的额外函数调用，简单拼接在文件末尾的 init 风格：
        return (
            user_code
            + "\n\nfunc init() {\n"
            + "\t// auto test — 请保证测试语句在 init 中合法\n"
            + _indent_go_test(test)
            + "}\n"
        )
    if lang == "java":
        # 在 Main.main 末尾注入很脆；改为再写一个 TestRunner 太复杂。
        # 简单策略：若代码含 main，在类里追加 static 块跑 assert 风格不方便。
        # 用临时包装：用户代码需是完整 Main 类时，在 main 末尾前不改；改为单独执行测试字符串若以 assert 开头则跳过提示。
        return (
            user_code.replace(
                "public static void main(String[] args) {",
                "public static void main(String[] args) {\n    // auto test begin\n    "
                + test.replace("\n", "\n    ")
                + "\n    // auto test end\n",
                1,
            )
            if "public static void main" in user_code
            else user_code
            + "\n// 无法自动注入 Java 测试：请保证存在 public static void main\n"
        )
    return user_code + "\n" + test


def _indent_go_test(test: str) -> str:
    lines = test.strip().splitlines() or ["_ = true"]
    return "".join("\t" + ln + "\n" for ln in lines)
