# FRAME — Full-stack Interview Demo (Vibe Coding)

[中文说明](#中文) · [English](#english) · **Guide**: [中文教程](./docs/guide.zh.md) / [English guide](./docs/guide.en.md)

Runnable media-ops loop: **NestJS** + **Next.js App Router (zh/en)** + SQLite indexes + RBAC + HLS + SEO + crawl + analytics + Nginx/PM2.

---

## 中文

### 快速启动

```bash
cd frame-ops-demo
npm install
npm run dev:api    # http://localhost:8787/api/health
npm run dev:web    # http://localhost:3088 → /zh 或 /en
```

| 入口 | 地址 |
|------|------|
| 中文首页 | http://localhost:3088/zh |
| 英文首页 | http://localhost:3088/en |
| **使用教程（站内）** | http://localhost:3088/zh/guide |
| 运营控制台 | http://localhost:3088/zh/ops |
| 详细文档 | [docs/guide.zh.md](./docs/guide.zh.md) |

演示账号：`admin@frame.demo` / `admin123`（另有 editor / viewer，密码为角色名+123）。

也可双击根目录启动脚本（推荐英文文件名，避免 cmd 编码问题）：

- `start-interview-tree.bat` — 启动 DeepSeek 面试题树桌面端（优先 EXE）
- `start-web-demo.bat` — 一键开 API + Web
- `启动面试题树.bat` / `启动Web演示.bat` — 同上（中文名包装）

### 多语言

- 路由前缀：`/zh/*`、`/en/*`
- 右上角切换语言；Cookie：`NEXT_LOCALE`
- 文案：`apps/web/src/i18n/dictionaries/`

### JD 对照（摘要）

Nest 守卫 / App Router 边界 / SQL 索引 / HLS·SEO / 分片上传 / 采集重试 / PV·UV·RBAC / Nginx·PM2 —— 详见教程第 5–9 节与 [docs/INTERVIEW.md](./docs/INTERVIEW.md)。

---

## English

### Quick start

```bash
cd frame-ops-demo
npm install
npm run dev:api    # http://localhost:8787/api/health
npm run dev:web    # http://localhost:3088 → /zh or /en
```

| Entry | URL |
|-------|-----|
| Home (EN) | http://localhost:3088/en |
| **In-app guide** | http://localhost:3088/en/guide |
| Ops console | http://localhost:3088/en/ops |
| Full guide | [docs/guide.en.md](./docs/guide.en.md) |

Demo login: `admin@frame.demo` / `admin123` (also editor/viewer).

### i18n

- Prefixes: `/zh/*`, `/en/*`
- Header language switch + `NEXT_LOCALE` cookie
- Dictionaries under `apps/web/src/i18n/dictionaries/`

---

## Layout

```
apps/api/                 NestJS API
apps/web/src/app/[locale] Localized UI (home / guide / ops / watch)
apps/web/src/i18n/        Locales + dictionaries
docs/guide.zh.md          Detailed Chinese tutorial
docs/guide.en.md          Detailed English tutorial
docs/INTERVIEW.md         Interview deep-dive
interview-tree-desktop/   Python desktop EXE: DeepSeek interview Q&A tree
deploy/                   Nginx + PM2
sql/schema.sql
```
