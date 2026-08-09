# -*- coding: utf-8 -*-
"""Default JD text for FRAME / fullstack Node+React interview prep."""

DEFAULT_JD = """岗位要求：
- 3 年以上 Node.js + React 实际项目经验，有完整交付过并维护过线上系统的经历
- TypeScript 熟练，理解泛型、类型收窄，能写出让下一个人看得懂的类型定义
- 熟悉 NestJS 或同类后端框架（Express/Koa/Egg 均可，但要理解依赖注入、中间件、守卫这套模型）
- 熟悉 Next.js App Router，能说清楚服务端组件与客户端组件的边界、SSR/ISR/CSR 各自的取舍
- SQL 与关系型数据库设计扎实 —— 会看执行计划、知道什么时候该加索引、理解事务与并发下的数据一致性
- 能独立完成 Linux 环境的部署与排障（Nginx、PM2、进程/端口/日志）

加分项：
- 做过视频/流媒体相关业务，了解 HLS/DASH、转码、CDN 分发
- 有 SEO 实战经验（SSR 首屏、结构化数据、sitemap、收录排查）
- 熟悉对象存储（S3/R2/OSS）与大文件分片上传
- 有内容采集/爬虫经验，了解反爬与容错设计
- 做过数据统计系统，理解 PV/UV/留存 的口径定义与埋点设计
- 有 RBAC 权限系统设计经验

硬性要求：
- Vibe coding（能用 AI 辅助快速交付可运行、可讲解的方案）

配套 Demo 线索（可写进答案）：
- FRAME 媒体运营控制台：NestJS + Next.js App Router（中英双语）+ SQLite 索引 + RBAC 守卫 + HLS/SEO + 分片上传 + 采集重试 + PV/UV + Nginx/PM2
"""

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"
