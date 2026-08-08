# 面试深挖备忘

## Nest 模型怎么讲

- **Provider / DI**：`DatabaseService` 挂在 `@Global() DatabaseModule`，各 feature service 构造器注入。
- **Middleware**：`RequestLogMiddleware` 在 `AppModule.configure` 挂到 `*`，先于守卫。
- **Guard**：`AuthGuard` 解析 Bearer；`PermissionsGuard` 读 `@RequirePermissions()` metadata。
- **Pipe**：全局 `ValidationPipe` whitelist + transform，DTO 用 class-validator。

## App Router 边界

| 页面 | 类型 | 原因 |
|------|------|------|
| `/` | RSC + ISR | SEO、目录缓存 |
| `/watch/[slug]` | RSC + ISR | 元数据 / JSON-LD |
| `/ops` | Client | 登录态、表格交互 |
| `TrackView` | Client | `localStorage` 访客 ID |

## 流媒体

Master playlist 返回多码率 ladder。生产链路：源片 → 转码（H.264/AAC）→ fMP4/TS 切片 → 上传 OSS → CDN（按 path 缓存，m3u8 短 TTL，ts/m4s 长 TTL）。

## 分片上传 → 对象存储

Demo 写本地 `data/objects`。替换点：

1. `init` → `CreateMultipartUpload`
2. `chunks/:i` → `UploadPart`
3. `complete` → `CompleteMultipartUpload`

## 排障清单

1. `ss -lntp | grep -E '8787|3088'` 看端口
2. `pm2 logs frame-api --lines 200`
3. `tail -f /var/log/nginx/frame.error.log`
4. 502：上游挂了或 proxy_pass 少尾斜杠
5. 413：`client_max_body_size`
6. HLS 跨域：CDN / Nginx `Access-Control-Allow-Origin`
