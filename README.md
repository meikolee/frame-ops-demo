# FRAME — 全栈面试 Demo（Vibe Coding）

对照岗位 JD 做的**可运行最小闭环**：NestJS API + Next.js App Router + SQLite（含索引设计）+ RBAC + 分片上传 + HLS 清单 + SEO + 采集重试 + PV/UV + Nginx/PM2。

> 目标不是堆功能，而是面试时能**边跑边讲**：依赖注入 / 守卫 / RSC 边界 / 执行计划 / 部署排障。

---

## 快速启动

```bash
cd frame-ops-demo
npm install
npm run build -w @frame/shared
npm run dev:api    # http://localhost:8787/api/health
npm run dev:web    # http://localhost:3088
```

演示账号：

| Email | Password | Role |
|-------|----------|------|
| admin@frame.demo | admin123 | admin |
| editor@frame.demo | editor123 | editor |
| viewer@frame.demo | viewer123 | viewer |

---

## JD 能力对照

| 要求 | Demo 落点 |
|------|-----------|
| Node.js + React 线上交付感 | `apps/api` + `apps/web`，含 seed 数据与健康检查 |
| TypeScript 泛型 / 收窄 | `packages/shared`：`ApiResult<T>`、`isRole`、`unwrap` |
| NestJS DI / 中间件 / 守卫 | `DatabaseModule`、`RequestLogMiddleware`、`AuthGuard` + `PermissionsGuard` |
| Next.js App Router 边界 | 首页/详情 = Server Component + ISR；`/ops` + `TrackView` = Client |
| SSR / ISR / CSR | `revalidate` 首页 60s、详情 30s；控制台 `cache: 'no-store'` |
| SQL 索引 / 事务 | `sql/schema.sql` + 上传完成事务；README 含 EXPLAIN 讲法 |
| Linux 部署排障 | `deploy/nginx.conf`、`deploy/ecosystem.config.cjs` |
| HLS / CDN | `GET /api/videos/:id/hls/master.m3u8` 多码率 master |
| SEO | metadata、JSON-LD `VideoObject`、`sitemap.ts`、`robots.ts` |
| 对象存储分片上传 | `UploadService` 本地 objects 根，可替换 S3/R2/OSS |
| 采集 / 反爬 / 容错 | `CrawlService` UA、超时、指数退避、attempt cap |
| PV/UV/留存 + 埋点 | `AnalyticsService.summary` 口径注释 + `TrackView` |
| RBAC | role → permission 矩阵，守卫按权限拒绝 |
| **Vibe coding** | 本仓库即一次 vibe 交付：可跑、可讲、可扩 |

---

## 面试 5 分钟话术

1. 打开首页：讲 **SSR 首屏 + ISR**，点进 watch 页讲 **JSON-LD / sitemap**。
2. 打开 `/ops` 用 admin 登录：讲 **Bearer + PermissionsGuard**，看 PV/UV/D1 口径。
3. 用 viewer 登录再调 crawl：讲 **403 = 权限模型生效**。
4. 打开 `sql/schema.sql`：讲 `idx_videos_status_published` 与 `EXPLAIN QUERY PLAN`。
5. 打开 `deploy/`：讲 Nginx 反代、PM2 日志路径、端口与 `client_max_body_size`。

### 渲染策略取舍（常考）

- **SSR**：SEO / 首屏关键，详情页要索引。
- **ISR**：目录页可接受 60s 陈旧，减峰时压力。
- **CSR**：控制台强交互、强鉴权，不需要被收录。

### SQL 常考

```sql
EXPLAIN QUERY PLAN
SELECT slug, title FROM videos
WHERE status = 'published'
ORDER BY published_at DESC
LIMIT 20;
-- 期望走 idx_videos_status_published
```

何时加索引：高基数过滤列 + 排序列；避免低选择性单列滥加。事务边界：分片收齐后「组装对象 + 改状态」同事务，避免半成品对外可见。

---

## 目录

```
frame-ops-demo/
  apps/api/          NestJS
  apps/web/          Next.js 15 App Router
  packages/shared/   共享类型与 RBAC
  sql/schema.sql
  deploy/            Nginx + PM2
  docs/INTERVIEW.md
```
