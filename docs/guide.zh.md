# FRAME 详细使用教程（中文）

> 在线版（推荐边点边看）：启动 Web 后打开 [http://localhost:3088/zh/guide](http://localhost:3088/zh/guide)  
> English: [docs/guide.en.md](./guide.en.md) · [http://localhost:3088/en/guide](http://localhost:3088/en/guide)

---

## 0. 你将得到什么

一套可运行的全栈面试 Demo，覆盖：

- NestJS：依赖注入、中间件、守卫、RBAC
- Next.js App Router：RSC / CSR 边界、SSR / ISR、多语言路由 `/zh` `/en`
- SQL：索引设计、事务边界、EXPLAIN 讲法
- 媒体：HLS master、SEO（metadata / JSON-LD / sitemap）
- 运营：PV/UV/留存口径、采集重试、分片上传骨架
- 部署：Nginx + PM2 配置与排障顺序

---

## 1. 环境要求

| 项 | 要求 |
|----|------|
| Node.js | **20+**（推荐 LTS） |
| 包管理 | npm（仓库含 `package-lock.json`） |
| 系统 | Windows / macOS / Linux 均可 |
| 端口 | `8787`（API）、`3088`（Web）空闲 |

检查：

```bash
node -v
npm -v
```

---

## 2. 安装与启动

```bash
cd frame-ops-demo
npm install

# 终端 A
npm run dev:api

# 终端 B
npm run dev:web
```

验证：

```bash
# API 健康检查
curl http://localhost:8787/api/health
# 或 PowerShell
Invoke-RestMethod http://localhost:8787/api/health
```

浏览器打开：

- 中文首页：http://localhost:3088/zh  
- 英文首页：http://localhost:3088/en  
- 根路径 `/` 会按浏览器语言协商后跳转到 `/zh` 或 `/en`

首次访问会自动建 SQLite：`apps/api/data/frame.sqlite`，并写入演示用户与视频。

---

## 3. 多语言怎么用

| 动作 | 说明 |
|------|------|
| URL 前缀 | `/zh/...` 中文，`/en/...` English |
| 右上角切换 | `SiteHeader` 语言切换，保留当前路径后缀 |
| Cookie | `NEXT_LOCALE`，中间件写入，刷新后保持 |
| 文案来源 | `apps/web/src/i18n/dictionaries/{zh,en}.ts` |
| SEO | `sitemap.xml` 含双语静态页与观看页；`html lang` 随 Cookie |

新增文案：同时改 `zh.ts` / `en.ts`，类型为 `Dictionary`。

---

## 4. 演示账号

| Email | Password | 角色 | 能力摘要 |
|-------|----------|------|----------|
| admin@frame.demo | admin123 | admin | 全部权限 |
| editor@frame.demo | editor123 | editor | 写视频 / 上传 / 采集 / 统计 |
| viewer@frame.demo | viewer123 | viewer | 只读视频与统计 |

权限矩阵在 `packages/shared/src/index.ts`（`ROLE_PERMISSIONS`）。

登录成功后 Token：`Bearer admin:u_admin`（形态 `role:userId`）。

---

## 5. 推荐操作路径（15 分钟）

### 5.1 首页（SSR / ISR）

1. 打开 `/zh`  
2. 观察首屏品牌区 +「已发布目录」  
3. 讲解点：Server Component、`revalidate = 60`（ISR）

### 5.2 观看页（SEO）

1. 点进 `aurora-cutdown`  
2. 查看页面源码中的 JSON-LD `VideoObject`  
3. 打开 `/sitemap.xml`、`/robots.txt`  
4. 讲解点：`generateMetadata`、结构化数据、收录路径

### 5.3 控制台（CSR + RBAC）

1. 打开 `/zh/ops`，用 **admin** 登录  
2. 看 Session 权限列表、Analytics（PV/UV/D1）、Videos  
3. Crawl 提交 `https://example.com/frame-demo`，等 succeeded  
4. 换 **viewer** 登录再点采集 → 预期 **403**（PermissionsGuard）

### 5.4 API 冒烟

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8787/api/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"admin@frame.demo","password":"admin123"}'
$token = $login.data.token
Invoke-RestMethod http://localhost:8787/api/analytics/summary?days=7 `
  -Headers @{ Authorization = "Bearer $token" }
```

### 5.5 SQL

打开 `sql/schema.sql`，在 sqlite3 中：

```sql
EXPLAIN QUERY PLAN
SELECT slug, title FROM videos
WHERE status = 'published'
ORDER BY published_at DESC
LIMIT 20;
```

期望走 `idx_videos_status_published`。

### 5.6 部署配置

阅读：

- `deploy/nginx.conf` — 反代、上传体积、HLS 缓存头  
- `deploy/ecosystem.config.cjs` — PM2 进程与日志路径  

排障顺序：端口 → `pm2 logs` → nginx error.log → 502 / 413。

---

## 6. 目录速查

```
frame-ops-demo/
  apps/api/                 NestJS
  apps/web/
    src/app/[locale]/      多语言页面（home / ops / watch / guide）
    src/i18n/               语言配置与字典
    src/middleware.ts       语言协商与跳转
  packages/shared/          ApiResult、RBAC
  sql/schema.sql
  deploy/
  docs/guide.zh.md          本文件
  docs/guide.en.md
  docs/INTERVIEW.md         面试深挖
```

---

## 7. 常见问题

**Q: 首页提示 API offline**  
A: 先确认 `npm run dev:api` 已启动且 `http://localhost:8787/api/health` 正常。

**Q: 登录 500 / 注入失败**  
A: API 使用显式 `@Inject()`（tsx 不发 decorator metadata）。不要删掉 `@Inject`。

**Q: 如何加第三种语言**  
A: 在 `locales` 增加代码 → 新建字典 → `dictionaries` 注册 → 补 sitemap。

**Q: 视频文案仍是英文？**  
A: Seed 数据在 `database.service.ts`；UI 外壳已双语。可按需把 seed 改成中英两套字段。

---

## 8. 五分钟面试演示脚本

1. `/zh` 讲 SSR/ISR  
2. 观看页讲 JSON-LD + sitemap  
3. `/zh/ops` admin 讲 Guard / RBAC / PV·UV 口径  
4. viewer 撞 403  
5. `schema.sql` 讲索引  
6. `deploy/` 讲 Nginx / PM2  
7. 点题：这是 **vibe coding** 可交付闭环  

更细的 Nest / 流媒体 / 分片上传替换点见 [INTERVIEW.md](./INTERVIEW.md)。
