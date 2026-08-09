# -*- coding: utf-8 -*-
"""本地实操：多语言编辑/运行 + 自测用例。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# 展示名 → 内部 id（面试常见语言尽量覆盖；均可编辑+AI补全，有运行器则可本地跑）
LANG_OPTIONS: list[tuple[str, str]] = [
    ("Python", "python"),
    ("JavaScript (Node)", "javascript"),
    ("TypeScript", "typescript"),
    ("Go", "go"),
    ("Java", "java"),
    ("C", "c"),
    ("C++", "cpp"),
    ("C#", "csharp"),
    ("Rust", "rust"),
    ("Kotlin", "kotlin"),
    ("Swift", "swift"),
    ("Ruby", "ruby"),
    ("PHP", "php"),
    ("Scala", "scala"),
    ("Dart", "dart"),
    ("Bash", "bash"),
    ("PowerShell", "powershell"),
    ("SQL (SQLite)", "sql"),
    ("R", "r"),
    ("Lua", "lua"),
    ("Perl", "perl"),
    ("Elixir", "elixir"),
    ("Haskell", "haskell"),
    ("Zig", "zig"),
    ("Nim", "nim"),
    ("Groovy", "groovy"),
    ("Objective-C", "objc"),
    ("Julia", "julia"),
    ("Fortran", "fortran"),
    ("VB.NET", "vbnet"),
]

LANG_LABELS = {lid: label for label, lid in LANG_OPTIONS}

_ALIASES = {
    "py": "python",
    "js": "javascript",
    "node": "javascript",
    "ts": "typescript",
    "golang": "go",
    "c++": "cpp",
    "cplusplus": "cpp",
    "cs": "csharp",
    "c#": "csharp",
    "rs": "rust",
    "kt": "kotlin",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "ps": "powershell",
    "ps1": "powershell",
    "sqlite": "sql",
    "sqlite3": "sql",
    "rlang": "r",
    "objective-c": "objc",
    "objectivec": "objc",
    "vb": "vbnet",
    "visualbasic": "vbnet",
}


def _starter(comment: str, body: str) -> str:
    return f"{comment}\n{body.rstrip()}\n"


STARTERS: dict[str, str] = {
    "python": _starter(
        "# write your code",
        "def solve():\n    pass\n\nif __name__ == '__main__':\n    print(solve())",
    ),
    "javascript": _starter(
        "// write your code",
        "function solve() {\n  // TODO\n}\n\nconsole.log(solve());",
    ),
    "typescript": _starter(
        "// write your code",
        "function solve(): unknown {\n  // TODO\n  return null;\n}\n\nconsole.log(solve());",
    ),
    "go": (
        "package main\n\nimport \"fmt\"\n\n"
        "func solve() any {\n\t// TODO\n\treturn nil\n}\n\n"
        "func main() {\n\tfmt.Println(solve())\n}\n"
    ),
    "java": (
        "public class Main {\n"
        "  static Object solve() {\n    // TODO\n    return null;\n  }\n"
        "  public static void main(String[] args) {\n"
        "    System.out.println(solve());\n  }\n}\n"
    ),
    "c": (
        "#include <stdio.h>\n\nint main(void) {\n"
        "  /* TODO */\n  printf(\"ok\\n\");\n  return 0;\n}\n"
    ),
    "cpp": (
        "#include <iostream>\nusing namespace std;\n\nint main() {\n"
        "  // TODO\n  cout << \"ok\" << endl;\n  return 0;\n}\n"
    ),
    "csharp": (
        "using System;\nclass Program {\n"
        "  static void Main() {\n    // TODO\n    Console.WriteLine(\"ok\");\n  }\n}\n"
    ),
    "rust": (
        "fn main() {\n    // TODO\n    println!(\"ok\");\n}\n"
    ),
    "kotlin": (
        "fun main() {\n    // TODO\n    println(\"ok\")\n}\n"
    ),
    "swift": (
        "import Foundation\n\n// TODO\nprint(\"ok\")\n"
    ),
    "ruby": _starter("# write your code", "def solve\n  # TODO\nend\n\nputs solve"),
    "php": "<?php\n// write your code\nfunction solve() {\n  // TODO\n}\necho solve();\n",
    "scala": (
        "object Main extends App {\n  // TODO\n  println(\"ok\")\n}\n"
    ),
    "dart": (
        "void main() {\n  // TODO\n  print('ok');\n}\n"
    ),
    "bash": "#!/usr/bin/env bash\nset -euo pipefail\n# TODO\necho ok\n",
    "powershell": "# write your code\nWrite-Output 'ok'\n",
    "sql": "-- write your SQL\nSELECT 1 AS ok;\n",
    "r": "# write your code\ncat('ok\\n')\n",
    "lua": "-- write your code\nprint('ok')\n",
    "perl": "#!/usr/bin/env perl\nuse strict;\nuse warnings;\nprint \"ok\\n\";\n",
    "elixir": "IO.puts(\"ok\")\n",
    "haskell": "main :: IO ()\nmain = putStrLn \"ok\"\n",
    "zig": (
        "const std = @import(\"std\");\n"
        "pub fn main() void {\n    std.debug.print(\"ok\\n\", .{});\n}\n"
    ),
    "nim": "echo \"ok\"\n",
    "groovy": "println 'ok'\n",
    "objc": (
        "#import <Foundation/Foundation.h>\n"
        "int main(int argc, const char * argv[]) {\n"
        "  @autoreleasepool {\n    NSLog(@\"ok\");\n  }\n  return 0;\n}\n"
    ),
    "julia": "println(\"ok\")\n",
    "fortran": (
        "program main\n  print *, 'ok'\nend program main\n"
    ),
    "vbnet": (
        "Module Program\n  Sub Main()\n    ' TODO\n    Console.WriteLine(\"ok\")\n  End Sub\nEnd Module\n"
    ),
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
    s = _ALIASES.get(s, s)
    if s in LANG_LABELS:
        return s
    # 未知 id：尽量保留，便于 AI 补全；运行会提示无本机运行器
    return s or "python"


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def runtime_status(lang: str) -> tuple[bool, str]:
    """返回 (可用?, 说明)。不可跑时仍可编辑 / DeepSeek 补全。"""
    lang = normalize_lang(lang)
    if lang == "python":
        return True, sys.executable
    if lang == "javascript":
        p = which("node")
        return (bool(p), p or "未找到 node；仍可编辑与 AI 补全")
    if lang == "typescript":
        if which("tsx"):
            return True, "tsx"
        if which("npx"):
            return True, "npx tsx"
        if which("ts-node"):
            return True, "ts-node"
        return False, "未找到 tsx/npx/ts-node；仍可编辑与 AI 补全"
    if lang == "go":
        p = which("go")
        return (bool(p), p or "未找到 go；仍可编辑与 AI 补全")
    if lang == "java":
        javac, java = which("javac"), which("java")
        if javac and java:
            return True, f"{javac} + {java}"
        return False, "未找到 JDK；仍可编辑与 AI 补全"
    if lang == "c":
        p = which("gcc") or which("clang")
        return (bool(p), p or "未找到 gcc/clang；仍可编辑与 AI 补全")
    if lang == "cpp":
        p = which("g++") or which("clang++")
        return (bool(p), p or "未找到 g++/clang++；仍可编辑与 AI 补全")
    if lang == "csharp":
        if which("dotnet"):
            return True, "dotnet"
        if which("csc"):
            return True, "csc"
        return False, "未找到 dotnet/csc；仍可编辑与 AI 补全"
    if lang == "rust":
        p = which("rustc")
        return (bool(p), p or "未找到 rustc；仍可编辑与 AI 补全")
    if lang == "kotlin":
        if which("kotlinc") and which("java"):
            return True, "kotlinc"
        if which("kotlin"):
            return True, "kotlin"
        return False, "未找到 kotlinc；仍可编辑与 AI 补全"
    if lang == "swift":
        p = which("swift")
        return (bool(p), p or "未找到 swift；仍可编辑与 AI 补全")
    if lang == "ruby":
        p = which("ruby")
        return (bool(p), p or "未找到 ruby；仍可编辑与 AI 补全")
    if lang == "php":
        p = which("php")
        return (bool(p), p or "未找到 php；仍可编辑与 AI 补全")
    if lang == "scala":
        p = which("scala") or which("scalac")
        return (bool(p), p or "未找到 scala；仍可编辑与 AI 补全")
    if lang == "dart":
        p = which("dart")
        return (bool(p), p or "未找到 dart；仍可编辑与 AI 补全")
    if lang == "bash":
        p = which("bash") or which("sh")
        return (bool(p), p or "未找到 bash；仍可编辑与 AI 补全")
    if lang == "powershell":
        p = which("pwsh") or which("powershell")
        return (bool(p), p or "未找到 PowerShell；仍可编辑与 AI 补全")
    if lang == "sql":
        p = which("sqlite3")
        return (bool(p), p or "未找到 sqlite3；仍可编辑与 AI 补全")
    if lang == "r":
        p = which("Rscript")
        return (bool(p), p or "未找到 Rscript；仍可编辑与 AI 补全")
    if lang == "lua":
        p = which("lua") or which("luajit")
        return (bool(p), p or "未找到 lua；仍可编辑与 AI 补全")
    if lang == "perl":
        p = which("perl")
        return (bool(p), p or "未找到 perl；仍可编辑与 AI 补全")
    if lang == "elixir":
        p = which("elixir")
        return (bool(p), p or "未找到 elixir；仍可编辑与 AI 补全")
    if lang == "haskell":
        p = which("runhaskell") or which("ghc")
        return (bool(p), p or "未找到 runhaskell/ghc；仍可编辑与 AI 补全")
    if lang == "zig":
        p = which("zig")
        return (bool(p), p or "未找到 zig；仍可编辑与 AI 补全")
    if lang == "nim":
        p = which("nim")
        return (bool(p), p or "未找到 nim；仍可编辑与 AI 补全")
    if lang == "groovy":
        p = which("groovy")
        return (bool(p), p or "未找到 groovy；仍可编辑与 AI 补全")
    if lang == "objc":
        p = which("clang")
        return (bool(p), p or "未找到 clang；仍可编辑与 AI 补全")
    if lang == "julia":
        p = which("julia")
        return (bool(p), p or "未找到 julia；仍可编辑与 AI 补全")
    if lang == "fortran":
        p = which("gfortran")
        return (bool(p), p or "未找到 gfortran；仍可编辑与 AI 补全")
    if lang == "vbnet":
        if which("dotnet"):
            return True, "dotnet"
        if which("vbc"):
            return True, "vbc"
        return False, "未找到 dotnet/vbc；仍可编辑与 AI 补全"
    label = LANG_LABELS.get(lang, lang)
    return False, f"「{label}」本地暂无运行器；仍可编辑与 AI 补全"


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


def _fail(msg: str, lang: str) -> dict[str, Any]:
    return {
        "ok": False,
        "returncode": -1,
        "stdout": "",
        "stderr": msg,
        "timed_out": False,
        "language": lang,
    }


def run_snippet(lang: str, code: str, timeout: float = 8.0) -> dict[str, Any]:
    """按语言执行代码片段。"""
    lang = normalize_lang(lang)
    ok, info = runtime_status(lang)
    if not ok:
        return _fail(info, lang)

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
            result = _run_cmd(cmd, root, max(timeout, 60.0))
        elif lang == "go":
            path = root / "main.go"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["go", "run", str(path)], root, timeout)
        elif lang == "java":
            path = root / "Main.java"
            path.write_text(code, encoding="utf-8")
            c = _run_cmd(["javac", str(path)], root, timeout)
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd(["java", "-cp", str(root), "Main"], root, timeout)
        elif lang == "c":
            src = root / "main.c"
            exe = root / ("main.exe" if os.name == "nt" else "main")
            src.write_text(code, encoding="utf-8")
            cc = which("gcc") or which("clang")
            c = _run_cmd([cc, str(src), "-o", str(exe)], root, timeout)  # type: ignore[list-item]
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd([str(exe)], root, timeout)
        elif lang == "cpp":
            src = root / "main.cpp"
            exe = root / ("main.exe" if os.name == "nt" else "main")
            src.write_text(code, encoding="utf-8")
            cxx = which("g++") or which("clang++")
            c = _run_cmd([cxx, str(src), "-o", str(exe)], root, timeout)  # type: ignore[list-item]
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd([str(exe)], root, timeout)
        elif lang == "csharp":
            path = root / "Program.cs"
            path.write_text(code, encoding="utf-8")
            if which("dotnet"):
                # 临时控制台项目
                _run_cmd(
                    ["dotnet", "new", "console", "-n", "Lab", "--force"],
                    root,
                    max(timeout, 60.0),
                )
                proj = root / "Lab"
                (proj / "Program.cs").write_text(code, encoding="utf-8")
                result = _run_cmd(
                    ["dotnet", "run", "--project", str(proj)],
                    root,
                    max(timeout, 60.0),
                )
            else:
                exe = root / "Program.exe"
                c = _run_cmd(["csc", f"/out:{exe}", str(path)], root, timeout)
                if not c.get("ok"):
                    c["language"] = lang
                    return c
                result = _run_cmd([str(exe)], root, timeout)
        elif lang == "rust":
            src = root / "main.rs"
            exe = root / ("main.exe" if os.name == "nt" else "main")
            src.write_text(code, encoding="utf-8")
            c = _run_cmd(["rustc", str(src), "-o", str(exe)], root, timeout)
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd([str(exe)], root, timeout)
        elif lang == "kotlin":
            src = root / "Main.kt"
            src.write_text(code, encoding="utf-8")
            if which("kotlinc"):
                jar = root / "main.jar"
                c = _run_cmd(
                    ["kotlinc", str(src), "-include-runtime", "-d", str(jar)],
                    root,
                    max(timeout, 30.0),
                )
                if not c.get("ok"):
                    c["language"] = lang
                    return c
                result = _run_cmd(["java", "-jar", str(jar)], root, timeout)
            else:
                result = _run_cmd(["kotlin", str(src)], root, timeout)
        elif lang == "swift":
            path = root / "main.swift"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["swift", str(path)], root, timeout)
        elif lang == "ruby":
            path = root / "snippet.rb"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["ruby", str(path)], root, timeout)
        elif lang == "php":
            path = root / "snippet.php"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["php", str(path)], root, timeout)
        elif lang == "scala":
            path = root / "Main.scala"
            path.write_text(code, encoding="utf-8")
            if which("scala"):
                result = _run_cmd(["scala", str(path)], root, max(timeout, 30.0))
            else:
                c = _run_cmd(["scalac", str(path)], root, max(timeout, 30.0))
                if not c.get("ok"):
                    c["language"] = lang
                    return c
                result = _run_cmd(["scala", "Main"], root, timeout)
        elif lang == "dart":
            path = root / "snippet.dart"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["dart", "run", str(path)], root, timeout)
        elif lang == "bash":
            path = root / "snippet.sh"
            path.write_text(code, encoding="utf-8")
            shell = which("bash") or which("sh")
            result = _run_cmd([shell, str(path)], root, timeout)  # type: ignore[list-item]
        elif lang == "powershell":
            path = root / "snippet.ps1"
            path.write_text(code, encoding="utf-8")
            shell = which("pwsh") or which("powershell")
            result = _run_cmd(
                [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)],
                root,
                timeout,
            )  # type: ignore[list-item]
        elif lang == "sql":
            path = root / "snippet.sql"
            path.write_text(code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    ["sqlite3", ":memory:"],
                    input=code,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(root),
                )
                result = {
                    "ok": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout or "",
                    "stderr": proc.stderr or "",
                    "timed_out": False,
                }
            except subprocess.TimeoutExpired as e:
                result = {
                    "ok": False,
                    "returncode": -1,
                    "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
                    "stderr": f"执行超时（>{timeout}s）",
                    "timed_out": True,
                }
            except FileNotFoundError as e:
                result = {
                    "ok": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"找不到可执行文件：{e}",
                    "timed_out": False,
                }
        elif lang == "r":
            path = root / "snippet.R"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["Rscript", str(path)], root, timeout)
        elif lang == "lua":
            path = root / "snippet.lua"
            path.write_text(code, encoding="utf-8")
            lua = which("lua") or which("luajit")
            result = _run_cmd([lua, str(path)], root, timeout)  # type: ignore[list-item]
        elif lang == "perl":
            path = root / "snippet.pl"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["perl", str(path)], root, timeout)
        elif lang == "elixir":
            path = root / "snippet.exs"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["elixir", str(path)], root, timeout)
        elif lang == "haskell":
            path = root / "Main.hs"
            path.write_text(code, encoding="utf-8")
            if which("runhaskell"):
                result = _run_cmd(["runhaskell", str(path)], root, timeout)
            else:
                exe = root / ("Main.exe" if os.name == "nt" else "Main")
                c = _run_cmd(["ghc", str(path), "-o", str(exe)], root, max(timeout, 30.0))
                if not c.get("ok"):
                    c["language"] = lang
                    return c
                result = _run_cmd([str(exe)], root, timeout)
        elif lang == "zig":
            path = root / "main.zig"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["zig", "run", str(path)], root, max(timeout, 30.0))
        elif lang == "nim":
            path = root / "main.nim"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["nim", "c", "-r", "--hints:off", str(path)], root, max(timeout, 30.0))
        elif lang == "groovy":
            path = root / "snippet.groovy"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["groovy", str(path)], root, timeout)
        elif lang == "objc":
            src = root / "main.m"
            exe = root / ("main.exe" if os.name == "nt" else "main")
            src.write_text(code, encoding="utf-8")
            c = _run_cmd(
                ["clang", str(src), "-framework", "Foundation", "-o", str(exe)],
                root,
                timeout,
            )
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd([str(exe)], root, timeout)
        elif lang == "julia":
            path = root / "snippet.jl"
            path.write_text(code, encoding="utf-8")
            result = _run_cmd(["julia", str(path)], root, timeout)
        elif lang == "fortran":
            src = root / "main.f90"
            exe = root / ("main.exe" if os.name == "nt" else "main")
            src.write_text(code, encoding="utf-8")
            c = _run_cmd(["gfortran", str(src), "-o", str(exe)], root, timeout)
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd([str(exe)], root, timeout)
        elif lang == "vbnet":
            path = root / "Program.vb"
            path.write_text(code, encoding="utf-8")
            if which("dotnet"):
                return _fail("VB.NET 请改用 C# 模板或安装 vbc；dotnet 临时项目默认是 C#", lang)
            exe = root / "Program.exe"
            c = _run_cmd(["vbc", f"/out:{exe}", str(path)], root, timeout)
            if not c.get("ok"):
                c["language"] = lang
                return c
            result = _run_cmd([str(exe)], root, timeout)
        else:
            return _fail(f"不支持运行：{lang}", lang)
        result["language"] = lang
        return result


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
        return (
            user_code
            + "\n\nfunc init() {\n"
            + "\t// auto test\n"
            + _indent_lines(test, "\t")
            + "}\n"
        )
    if lang == "java":
        if "public static void main" in user_code:
            return user_code.replace(
                "public static void main(String[] args) {",
                "public static void main(String[] args) {\n    // auto test begin\n    "
                + test.replace("\n", "\n    ")
                + "\n    // auto test end\n",
                1,
            )
        return user_code + "\n// 无法自动注入 Java 测试\n"
    # 其他语言：简单拼接，依赖用例本身可执行
    return user_code + "\n\n" + test + "\n"


def _indent_lines(text: str, prefix: str) -> str:
    lines = text.strip().splitlines() or ["_ = true"]
    return "".join(prefix + ln + "\n" for ln in lines)
