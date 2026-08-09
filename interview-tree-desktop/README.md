# FRAME 面试题树桌面版（Python / EXE）

针对目标岗位 JD，用 DeepSeek 生成可不断展开生长的面试题与答案树；全部保存在本地，可联网同步更新。

界面使用 **tkinter（Python 自带）**，不依赖 PySide6/Qt，避免 Windows 上常见的 `DLL load failed while importing QtCore`。

## 功能

1. **输入框**：一键粘贴/编辑职位描述；填写 DeepSeek API Key / Base URL / Model  
2. **解析生成**：调用 DeepSeek，按 JD 生成一级（含少量二级）面试题树  
3. **树形生长**：选中任意节点 →「展开选中节点」继续向下追问  
4. **联网同步**：选中节点 →「联网同步」刷新答案并可追加新子题  
5. **刷新题树**：追加新题 / 补充已有答案与子题，**不删除**原有内容，且可**一键撤销**上次刷新  
6. **多题库**：可新建 / 切换 / 重命名 / 删除多棵独立题树（各有自己的题目与 JD）  
7. **树内搜索**：按题干 / 答案 / 标签过滤整棵树（Ctrl+F 聚焦搜索框）  
8. **刷题模式**：隐藏答案逐题背诵，随机抽题 / 上一题 / 下一题  
9. **复制答案 / 问答**：一键复制到剪贴板（Ctrl+Shift+A / Ctrl+Shift+C）  
10. **详情弹窗**：每个输入/输出框都有「弹窗」按钮，双击也可打开 80% 屏幕大窗口查看完整内容  
11. **答案重点 + 朗读**：参考答案支持「查看重点」与「朗读」（自动跳过标点）  
12. **划词查询**：在答案中双击/划选名词 → 选择 AI 或浏览器查询；查过的词会高亮，悬停显示浏览器摘要  
13. **实操编程题**：题树支持 `[实操]` 节点；「⑤ 生成实操编程题」追加 JD 相关编程小题；「实操实验室」可切换 Python / JavaScript / TypeScript / Go / Java，按本机已安装运行时执行、自测、查看参考实现  
14. **导出**：Markdown、HTML、PDF（PDF 内置中文字体）  
15. **自动备份**：每次保存前自动保留上一版 `*.bak`  
16. **离线可用**：无 Key 时可点「离线种子树」先练；之后再同步升级  
17. **本地保存**：`data/config.json`、`data/interview_tree.json`、`data/trees.json`  

快捷键：`Ctrl+F` 搜索 · `F5` 刷新题树 · `Ctrl+Shift+A` 复制答案 · `Ctrl+Shift+C` 复制问答

## 开发运行

```powershell
cd interview-tree-desktop
pip install -r requirements.txt
python app.py
```

或双击（推荐）：

- 仓库根目录 `start-interview-tree-python.bat` / `启动面试题树-Python.bat`（**始终 Python，不走 EXE**）
- 本目录 `start.bat`（同上，开发模式）
- 仓库根目录 `start-interview-tree.bat` / `启动面试题树.bat`（优先 EXE，否则 Python）

## 打包 EXE

双击仓库根目录：

- `build-interview-tree-exe.bat` / `打包面试题树EXE.bat`

或：

```powershell
cd interview-tree-desktop
.\build_exe.ps1
```

产物：

- `interview-tree-desktop/dist/FrameInterviewTree.exe`
- `frame-ops-demo/FrameInterviewTree.exe`（副本）

EXE 与 `data/` 同级时，配置会写在 EXE 旁的 `data/`（见下方说明）。打包前请先关闭正在运行的 EXE。

## 推荐使用流程

1. 打开软件（首次自动生成离线种子树）  
2. 填入 DeepSeek API Key，点「测试连接」  
3. 确认左侧 JD（已预填目标岗位）→「① 解析 JD 并生成题树」  
4. 选中一题 → 右侧看答案 →「② 展开」继续生长  
5. 隔几天改 JD 或想刷新答案 →「③ 联网同步选中节点」  
6. 「保存到本地」/「导出 Markdown」  

## 数据位置

默认：`interview-tree-desktop/data/`

| 文件 | 内容 |
|------|------|
| `config.json` | API Key、模型、JD 文本 |
| `interview_tree.json` | 默认题库（整棵题树） |
| `trees.json` | 题库清单（多棵树用） |
| `trees/t_*.json` | 新建的其他题库 |
| `*.json.bak` | 每次保存前的自动备份 |

## 注意

- API Key 只存在本地，不会上传到本仓库  
- 生成/展开耗时取决于 DeepSeek；请勿重复连点；后台任务会显示已等待秒数  
- 模型需支持较长 JSON 输出；默认 `deepseek-chat`  
- 导出 PDF 需要 `reportlab`；朗读需要 `pyttsx3` / `pywin32`（`requirements.txt` 已包含，启动脚本会自动安装）  
