# FRAME 面试题树桌面版（Python / EXE）

针对目标岗位 JD，用 DeepSeek 生成可不断展开生长的面试题与答案树；全部保存在本地，可联网同步更新。

## 功能

1. **输入框**：粘贴/编辑职位描述；填写 DeepSeek API Key / Base URL / Model  
2. **解析生成**：调用 DeepSeek，按 JD 生成一级（含少量二级）面试题树  
3. **树形生长**：选中任意节点 →「展开选中节点」继续向下追问  
4. **联网同步**：选中节点 →「联网同步」刷新答案并可追加新子题  
5. **本地保存**：`data/config.json`、`data/interview_tree.json`  
6. **离线可用**：无 Key 时可点「离线种子树」先练；之后再同步升级  
7. **导出 Markdown**：方便打印/背题  

## 开发运行

```powershell
cd interview-tree-desktop
pip install -r requirements.txt
python app.py
```

## 打包 EXE

```powershell
cd interview-tree-desktop
.\build_exe.ps1
```

产物：

- `interview-tree-desktop/dist/FrameInterviewTree.exe`
- `frame-ops-demo/FrameInterviewTree.exe`（副本）

EXE 与 `data/` 同级时，配置会写在 EXE 旁的 `data/`（见下方说明）。

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
| `interview_tree.json` | 整棵题树 |

## 注意

- API Key 只存在本地，不会上传到本仓库  
- 生成/展开耗时取决于 DeepSeek；请勿重复连点  
- 模型需支持较长 JSON 输出；默认 `deepseek-chat`  
