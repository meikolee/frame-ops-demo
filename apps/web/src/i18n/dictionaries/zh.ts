import type { Dictionary } from "../dictionaries/en";

export const zh: Dictionary = {
  meta: {
    title: "FRAME — 媒体运营控制台",
    description:
      "面试 Demo：Next.js App Router + NestJS 媒体运营 —— HLS、RBAC、统计、分片上传。",
    ogDescription: "用类型安全的方式交付视频业务。",
  },
  nav: {
    home: "首页",
    ops: "控制台",
    guide: "使用教程",
    watch: "观看",
  },
  lang: {
    label: "语言",
    zh: "中文",
    en: "English",
  },
  home: {
    kicker: "媒体控制室",
    lede:
      "类型安全的媒体运营 Demo —— NestJS 守卫、App Router 边界、SQL 索引与部署手册，一次跑通。",
    ctaWatch: "观看已发布成片",
    ctaOps: "打开运营控制台",
    ctaGuide: "阅读使用教程",
    catalogTitle: "已发布目录",
    catalogDesc: "SSR + ISR（60 秒再验证）。结构化数据在观看页。",
    apiDown: "API 未启动 —— 请先在 :8787 启动 @frame/api",
    views: "次观看",
    minutes: "分钟",
  },
  watch: {
    hls: "HLS master 清单",
    meta: "SSR 详情 · ISR 30 秒 · JSON-LD VideoObject · {views} 次记录观看",
    notFound: "未找到",
  },
  ops: {
    tag: "CSR 运营控制台 · 客户端组件",
    signIn: "登录",
    accounts:
      "演示账号：admin / editor / viewer @frame.demo —— 密码为对应角色名 + 123（如 admin123）。",
    email: "邮箱",
    password: "密码",
    signingIn: "登录中…",
    enter: "进入控制室",
    session: "会话",
    analytics: "数据统计（近 7 天）",
    noData: "暂无数据",
    analyticsHint:
      "PV = page_view 行数 · UV = 去重 visitor_id · D1 = 次日留存率",
    videos: "视频列表",
    title: "标题",
    status: "状态",
    slug: "Slug",
    crawl: "采集任务",
    enqueue: "入队",
    guideLink: "不会用？先看教程",
  },
  guide: {
    title: "使用教程",
    subtitle: "从安装到面试演示的完整走查，建议按章节顺序操作。",
    toc: "目录",
    sections: [
      {
        id: "overview",
        title: "1. 项目是什么",
        body: [
          "FRAME 是一个可运行的全栈面试 Demo：NestJS API + Next.js App Router + SQLite。",
          "它不是大而全的产品，而是把岗位要求里的关键能力（守卫、RSC 边界、索引、部署、HLS/SEO/RBAC 等）收成一条能点能讲的闭环。",
          "公开站（首页 / 观看页）偏 SEO；/ops 控制台偏鉴权与交互。",
        ],
      },
      {
        id: "install",
        title: "2. 环境与安装",
        body: [
          "需要 Node.js 20+。在仓库根目录执行：",
          "npm install",
          "然后分别启动 API 与 Web（两个终端）：",
          "npm run dev:api    → http://localhost:8787/api/health",
          "npm run dev:web    → http://localhost:3088 （会跳到 /zh 或 /en）",
          "健康检查返回 { ok: true } 即表示 API 就绪。",
        ],
      },
      {
        id: "accounts",
        title: "3. 演示账号与权限",
        body: [
          "admin@frame.demo / admin123 —— 全部权限（含 rbac:manage、crawl:run）",
          "editor@frame.demo / editor123 —— 可写视频、上传、采集、看统计",
          "viewer@frame.demo / viewer123 —— 只读视频与统计，采集会 403",
          "Token 形态为 Bearer <role>:<userId>，例如 admin:u_admin。控制台登录后会自动带上。",
        ],
      },
      {
        id: "home",
        title: "4. 首页走查（SSR / ISR）",
        body: [
          "打开 /zh 或 /en：首屏是 Server Component 渲染的品牌页 + 已发布目录。",
          "revalidate = 60，属于 ISR：内容可缓存约 60 秒再后台刷新。",
          "点「观看已发布成片」进入详情；点「打开运营控制台」进入 /ops。",
          "右上角可切换中文 / English，路径前缀会变为 /zh 或 /en。",
        ],
      },
      {
        id: "watch",
        title: "5. 观看页与 SEO",
        body: [
          "观看页路径：/[locale]/watch/[slug]，例如 /zh/watch/aurora-cutdown。",
          "页面带 generateMetadata（title/description/OG）与 JSON-LD VideoObject。",
          "TrackView 是客户端组件：水合后上报 page_view（访客 ID 存 localStorage）。",
          "HLS master：GET /api/videos/:id/hls/master.m3u8 —— 多码率 ladder，演示 CDN 源路径约定。",
          "站点地图：/sitemap.xml；robots：控制台路径 disallow。",
        ],
      },
      {
        id: "ops",
        title: "6. 控制台操作步骤",
        body: [
          "1）打开 /zh/ops，用 admin 登录。",
          "2）查看 Session 面板：角色与 permission 列表（来自共享包 RBAC 矩阵）。",
          "3）Analytics：PV / UV / D1 / Plays —— 口径写在 API AnalyticsService 注释里。",
          "4）Videos：草稿/处理中/已发布状态；点 slug 回观看页。",
          "5）Crawl：提交 https://example.com/frame-demo，观察 queued → running/retrying → succeeded。",
          "6）退出后改用 viewer 登录，再点采集 —— 应被 PermissionsGuard 拒绝（403）。",
        ],
      },
      {
        id: "api",
        title: "7. 常用 API",
        body: [
          "GET  /api/health",
          "POST /api/auth/login  { email, password }",
          "GET  /api/videos?status=published",
          "GET  /api/videos/public/:slug",
          "GET  /api/analytics/summary?days=7  （需 Bearer）",
          "POST /api/analytics/track",
          "POST /api/crawl  { url }  （需 crawl:run）",
          "POST /api/uploads/init → chunks → complete  （分片上传）",
          "PowerShell 示例：Invoke-RestMethod http://localhost:8787/api/health",
        ],
      },
      {
        id: "sql",
        title: "8. SQL 与索引怎么讲",
        body: [
          "打开 sql/schema.sql，关注 idx_videos_status_published、analytics 时间索引。",
          "在 sqlite3 中执行：",
          "EXPLAIN QUERY PLAN SELECT slug, title FROM videos WHERE status = 'published' ORDER BY published_at DESC LIMIT 20;",
          "期望走 status + published_at 组合索引。",
          "上传完成在事务里「组装对象 + 改状态」，避免半成品对外可见。",
        ],
      },
      {
        id: "deploy",
        title: "9. 部署与排障",
        body: [
          "deploy/nginx.conf：/ 反代 Web，/api/ 反代 Nest，/media/ 短缓存。",
          "deploy/ecosystem.config.cjs：PM2 拉起 frame-api 与 frame-web，日志分文件。",
          "排障顺序：端口占用 → pm2 logs → nginx error.log → 502/413（client_max_body_size）。",
          "更多面试深挖见仓库 docs/INTERVIEW.md 与 docs/guide.zh.md。",
        ],
      },
      {
        id: "interview",
        title: "10. 五分钟演示脚本",
        body: [
          "① 首页讲 SSR/ISR → ② 观看页讲 JSON-LD/sitemap → ③ admin 登录讲 Guard/RBAC → ④ 看 PV/UV 口径 → ⑤ viewer 撞 403 → ⑥ 打开 schema 讲索引 → ⑦ 指 deploy 讲 Nginx/PM2。",
          "强调：这是 vibe coding 交付物 —— 可跑、可讲、可替换真实 LLM/OSS/CDN。",
        ],
      },
    ],
  },
};
