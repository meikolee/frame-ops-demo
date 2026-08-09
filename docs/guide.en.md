# FRAME User Guide (English)

> In-app guide (recommended): [http://localhost:3088/en/guide](http://localhost:3088/en/guide)  
> 中文：[docs/guide.zh.md](./guide.zh.md) · [http://localhost:3088/zh/guide](http://localhost:3088/zh/guide)

---

## 0. What you get

A runnable full-stack interview demo covering:

- NestJS: DI, middleware, guards, RBAC
- Next.js App Router: RSC/CSR boundaries, SSR/ISR, locale routes `/zh` `/en`
- SQL: indexes, transactions, EXPLAIN talking points
- Media: HLS master, SEO (metadata / JSON-LD / sitemap)
- Ops: PV/UV/retention definitions, crawl retries, chunked upload skeleton
- Deploy: Nginx + PM2 configs and a troubleshooting order

---

## 1. Prerequisites

| Item | Requirement |
|------|-------------|
| Node.js | **20+** (LTS recommended) |
| Package manager | npm (`package-lock.json` included) |
| OS | Windows / macOS / Linux |
| Ports | `8787` (API), `3088` (Web) free |

```bash
node -v
npm -v
```

---

## 2. Install & start

```bash
cd frame-ops-demo
npm install

# Terminal A
npm run dev:api

# Terminal B
npm run dev:web
```

Verify:

```bash
curl http://localhost:8787/api/health
# PowerShell
Invoke-RestMethod http://localhost:8787/api/health
```

Open:

- Chinese home: http://localhost:3088/zh  
- English home: http://localhost:3088/en  
- `/` negotiates language and redirects to `/zh` or `/en`

First boot creates SQLite at `apps/api/data/frame.sqlite` with seed users and videos.

---

## 3. Internationalization

| Action | Detail |
|--------|--------|
| URL prefix | `/zh/...` Chinese, `/en/...` English |
| Header switcher | Keeps the path suffix while swapping locale |
| Cookie | `NEXT_LOCALE` set by middleware |
| Copy source | `apps/web/src/i18n/dictionaries/{zh,en}.ts` |
| SEO | Sitemap includes both locales; `html lang` follows cookie |

To add strings: update both dictionaries (`Dictionary` type).

---

## 4. Demo accounts

| Email | Password | Role | Summary |
|-------|----------|------|---------|
| admin@frame.demo | admin123 | admin | All permissions |
| editor@frame.demo | editor123 | editor | Write / upload / crawl / analytics |
| viewer@frame.demo | viewer123 | viewer | Read-only videos & analytics |

RBAC matrix: `packages/shared/src/index.ts` (`ROLE_PERMISSIONS`).

Token after login: `Bearer admin:u_admin` (`role:userId`).

---

## 5. Recommended 15-minute path

### 5.1 Home (SSR / ISR)

1. Open `/en`  
2. Brand hero + published catalog  
3. Talk about Server Components and `revalidate = 60`

### 5.2 Watch (SEO)

1. Open `aurora-cutdown`  
2. Inspect JSON-LD `VideoObject` in page source  
3. Check `/sitemap.xml` and `/robots.txt`  
4. Talk about `generateMetadata` and indexing

### 5.3 Ops (CSR + RBAC)

1. Open `/en/ops`, sign in as **admin**  
2. Review permissions, Analytics (PV/UV/D1), Videos  
3. Crawl `https://example.com/frame-demo` → succeeded  
4. Sign in as **viewer**, try crawl → expect **403**

### 5.4 API smoke

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8787/api/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"admin@frame.demo","password":"admin123"}'
$token = $login.data.token
Invoke-RestMethod http://localhost:8787/api/analytics/summary?days=7 `
  -Headers @{ Authorization = "Bearer $token" }
```

### 5.5 SQL

```sql
EXPLAIN QUERY PLAN
SELECT slug, title FROM videos
WHERE status = 'published'
ORDER BY published_at DESC
LIMIT 20;
```

Expect `idx_videos_status_published`.

### 5.6 Deploy

- `deploy/nginx.conf` — proxy split, upload size, HLS cache headers  
- `deploy/ecosystem.config.cjs` — PM2 apps and log files  

Debug order: ports → `pm2 logs` → nginx error.log → 502 / 413.

---

## 6. Layout cheat sheet

```
apps/web/src/app/[locale]/   localized pages
apps/web/src/i18n/            locale config + dictionaries
apps/web/src/middleware.ts    negotiation + redirect
docs/guide.en.md              this file
docs/guide.zh.md
docs/INTERVIEW.md
```

---

## 7. FAQ

**Home says API offline**  
Start `npm run dev:api` and confirm `/api/health`.

**Login 500 / undefined service**  
API uses explicit `@Inject()` because tsx does not emit decorator metadata.

**Add a third language**  
Extend `locales`, add a dictionary, register it, update sitemap.

**Seed video copy is still English**  
UI chrome is bilingual; seed titles live in `database.service.ts` if you want localized content rows.

---

## 8. Five-minute interview script

1. `/en` SSR/ISR  
2. Watch JSON-LD + sitemap  
3. `/en/ops` admin Guard/RBAC/metrics  
4. viewer 403  
5. schema indexes  
6. Nginx/PM2  
7. Close with: vibe-coding deliverable — runnable and explainable  

See [INTERVIEW.md](./INTERVIEW.md) for deeper Nest / streaming / multipart swap notes.
