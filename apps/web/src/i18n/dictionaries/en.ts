export type Dictionary = {
  meta: {
    title: string;
    description: string;
    ogDescription: string;
  };
  nav: {
    home: string;
    ops: string;
    guide: string;
    watch: string;
  };
  lang: {
    label: string;
    zh: string;
    en: string;
  };
  home: {
    kicker: string;
    lede: string;
    ctaWatch: string;
    ctaOps: string;
    ctaGuide: string;
    catalogTitle: string;
    catalogDesc: string;
    apiDown: string;
    views: string;
    minutes: string;
  };
  watch: {
    hls: string;
    meta: string;
    notFound: string;
  };
  ops: {
    tag: string;
    signIn: string;
    accounts: string;
    email: string;
    password: string;
    signingIn: string;
    enter: string;
    session: string;
    analytics: string;
    noData: string;
    analyticsHint: string;
    videos: string;
    title: string;
    status: string;
    slug: string;
    crawl: string;
    enqueue: string;
    guideLink: string;
  };
  guide: {
    title: string;
    subtitle: string;
    toc: string;
    sections: Array<{ id: string; title: string; body: string[] }>;
  };
};

export const en: Dictionary = {
  meta: {
    title: "FRAME — Media Ops Console",
    description:
      "Interview demo: Next.js App Router + NestJS media ops — HLS, RBAC, analytics, chunked upload.",
    ogDescription: "Ship video with type-safe ops.",
  },
  nav: {
    home: "Home",
    ops: "Ops",
    guide: "Guide",
    watch: "Watch",
  },
  lang: {
    label: "Language",
    zh: "中文",
    en: "English",
  },
  home: {
    kicker: "MEDIA CONTROL ROOM",
    lede:
      "Type-safe media ops — NestJS guards, App Router boundaries, SQL indexes, and deploy playbooks in one runnable demo.",
    ctaWatch: "Watch published reel",
    ctaOps: "Open ops console",
    ctaGuide: "Read the guide",
    catalogTitle: "Published catalog",
    catalogDesc: "SSR + ISR (revalidate 60s). Structured data lives on each watch page.",
    apiDown: "API offline — start @frame/api on :8787",
    views: "views",
    minutes: "m",
  },
  watch: {
    hls: "HLS master",
    meta: "SSR detail · ISR 30s · JSON-LD VideoObject · {views} recorded views",
    notFound: "Not found",
  },
  ops: {
    tag: "CSR ops console · client components",
    signIn: "Sign in",
    accounts:
      "Demo accounts: admin / editor / viewer @frame.demo — passwords are role + 123 (e.g. admin123).",
    email: "Email",
    password: "Password",
    signingIn: "Signing in…",
    enter: "Enter control room",
    session: "Session",
    analytics: "Analytics (7d)",
    noData: "No data",
    analyticsHint:
      "PV = page_view rows · UV = distinct visitor_id · D1 = day-1 retention",
    videos: "Videos",
    title: "Title",
    status: "Status",
    slug: "Slug",
    crawl: "Crawl job",
    enqueue: "Enqueue",
    guideLink: "New here? Read the guide",
  },
  guide: {
    title: "User Guide",
    subtitle:
      "End-to-end walkthrough from install to interview demo. Follow the sections in order.",
    toc: "Contents",
    sections: [
      {
        id: "overview",
        title: "1. What this project is",
        body: [
          "FRAME is a runnable full-stack interview demo: NestJS API + Next.js App Router + SQLite.",
          "It is not a full product — it packages JD skills (guards, RSC boundaries, indexes, deploy, HLS/SEO/RBAC) into one clickable loop.",
          "Public pages (home / watch) lean SEO; /ops leans auth and interaction.",
        ],
      },
      {
        id: "install",
        title: "2. Prerequisites & install",
        body: [
          "Requires Node.js 20+. From the repo root:",
          "npm install",
          "Start API and Web in two terminals:",
          "npm run dev:api    → http://localhost:8787/api/health",
          "npm run dev:web    → http://localhost:3088 (redirects to /zh or /en)",
          "Health check returning { ok: true } means the API is ready.",
        ],
      },
      {
        id: "accounts",
        title: "3. Demo accounts & permissions",
        body: [
          "admin@frame.demo / admin123 — full permissions (including rbac:manage, crawl:run)",
          "editor@frame.demo / editor123 — write videos, upload, crawl, read analytics",
          "viewer@frame.demo / viewer123 — read-only videos/analytics; crawl returns 403",
          "Token shape is Bearer <role>:<userId>, e.g. admin:u_admin. The console attaches it after login.",
        ],
      },
      {
        id: "home",
        title: "4. Home walkthrough (SSR / ISR)",
        body: [
          "Open /zh or /en: brand hero + published catalog rendered as Server Components.",
          "revalidate = 60 → ISR: cache about 60s then revalidate in the background.",
          "Use “Watch published reel” for detail; “Open ops console” for /ops.",
          "Top-right language switch toggles /zh ↔ /en path prefixes.",
        ],
      },
      {
        id: "watch",
        title: "5. Watch page & SEO",
        body: [
          "Path: /[locale]/watch/[slug], e.g. /en/watch/aurora-cutdown.",
          "Uses generateMetadata (title/description/OG) plus JSON-LD VideoObject.",
          "TrackView is a Client Component: fires page_view after hydration (visitor id in localStorage).",
          "HLS master: GET /api/videos/:id/hls/master.m3u8 — multi-bitrate ladder for CDN path conventions.",
          "Sitemap: /sitemap.xml; robots disallow the ops console path.",
        ],
      },
      {
        id: "ops",
        title: "6. Ops console steps",
        body: [
          "1) Open /en/ops and sign in as admin.",
          "2) Session panel: role + permission list from the shared RBAC matrix.",
          "3) Analytics: PV / UV / D1 / Plays — definitions live in AnalyticsService comments.",
          "4) Videos: draft/processing/published; click slug to open the watch page.",
          "5) Crawl: submit https://example.com/frame-demo and watch queued → running/retrying → succeeded.",
          "6) Sign in as viewer and try crawl — PermissionsGuard should return 403.",
        ],
      },
      {
        id: "api",
        title: "7. Common APIs",
        body: [
          "GET  /api/health",
          "POST /api/auth/login  { email, password }",
          "GET  /api/videos?status=published",
          "GET  /api/videos/public/:slug",
          "GET  /api/analytics/summary?days=7  (Bearer required)",
          "POST /api/analytics/track",
          "POST /api/crawl  { url }  (needs crawl:run)",
          "POST /api/uploads/init → chunks → complete  (multipart upload)",
          "PowerShell: Invoke-RestMethod http://localhost:8787/api/health",
        ],
      },
      {
        id: "sql",
        title: "8. SQL & indexes talking points",
        body: [
          "Open sql/schema.sql — focus on idx_videos_status_published and analytics time indexes.",
          "In sqlite3:",
          "EXPLAIN QUERY PLAN SELECT slug, title FROM videos WHERE status = 'published' ORDER BY published_at DESC LIMIT 20;",
          "Expect the composite status + published_at index.",
          "Upload completion runs assemble + status update in one transaction so partial objects stay private.",
        ],
      },
      {
        id: "deploy",
        title: "9. Deploy & troubleshooting",
        body: [
          "deploy/nginx.conf: / → Web, /api/ → Nest, /media/ short cache.",
          "deploy/ecosystem.config.cjs: PM2 for frame-api and frame-web with split logs.",
          "Debug order: ports → pm2 logs → nginx error.log → 502/413 (client_max_body_size).",
          "Deeper notes: docs/INTERVIEW.md and docs/guide.en.md.",
        ],
      },
      {
        id: "interview",
        title: "10. Five-minute demo script",
        body: [
          "① Home SSR/ISR → ② Watch JSON-LD/sitemap → ③ admin Guard/RBAC → ④ PV/UV definitions → ⑤ viewer 403 → ⑥ schema indexes → ⑦ Nginx/PM2 deploy.",
          "Pitch: a vibe-coding deliverable — runnable, explainable, swappable to real LLM/OSS/CDN.",
        ],
      },
    ],
  },
};
