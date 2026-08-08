/** Roles used by RBAC guards on both API and web. */
export const ROLES = ["viewer", "editor", "admin"] as const;
export type Role = (typeof ROLES)[number];

export function isRole(value: unknown): value is Role {
  return typeof value === "string" && (ROLES as readonly string[]).includes(value);
}

/** Permission bits — derived from role, never stored loosely as strings in checks. */
export type Permission =
  | "video:read"
  | "video:write"
  | "video:publish"
  | "upload:write"
  | "analytics:read"
  | "crawl:run"
  | "rbac:manage";

const ROLE_PERMISSIONS: Record<Role, readonly Permission[]> = {
  viewer: ["video:read", "analytics:read"],
  editor: [
    "video:read",
    "video:write",
    "video:publish",
    "upload:write",
    "analytics:read",
    "crawl:run",
  ],
  admin: [
    "video:read",
    "video:write",
    "video:publish",
    "upload:write",
    "analytics:read",
    "crawl:run",
    "rbac:manage",
  ],
};

export function permissionsFor(role: Role): readonly Permission[] {
  return ROLE_PERMISSIONS[role];
}

export function hasPermission(role: Role, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role].includes(permission);
}

export type VideoStatus = "draft" | "processing" | "ready" | "published";

export interface VideoAsset {
  id: string;
  slug: string;
  title: string;
  summary: string;
  status: VideoStatus;
  durationSec: number;
  hlsPath: string | null;
  posterUrl: string | null;
  viewCount: number;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** Generic API envelope — callers narrow `data` via discriminators / generics. */
export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: { code: string; message: string } };

export function ok<T>(data: T): ApiResult<T> {
  return { ok: true, data };
}

export function fail(code: string, message: string): ApiResult<never> {
  return { ok: false, error: { code, message } };
}

export function unwrap<T>(result: ApiResult<T>): T {
  if (!result.ok) {
    throw new Error(`${result.error.code}: ${result.error.message}`);
  }
  return result.data;
}

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  role: Role;
}

export type AnalyticsEventName = "page_view" | "video_play" | "video_complete" | "cta_click";

export interface AnalyticsEventInput {
  name: AnalyticsEventName;
  path: string;
  visitorId: string;
  sessionId: string;
  videoId?: string;
  meta?: Record<string, string | number | boolean>;
}

export interface AnalyticsSummary {
  /** Unique page loads in range (event rows). */
  pv: number;
  /** Distinct visitorId in range. */
  uv: number;
  /** Visitors seen on day 0 who returned on day N (demo: N=1). */
  d1Retention: number;
  plays: number;
  completes: number;
}

export interface ChunkInitRequest {
  filename: string;
  mimeType: string;
  sizeBytes: number;
  chunkSize: number;
}

export interface ChunkInitResponse {
  uploadId: string;
  key: string;
  chunkSize: number;
  totalChunks: number;
}

export interface CrawlJob {
  id: string;
  url: string;
  status: "queued" | "running" | "succeeded" | "failed" | "retrying";
  attempts: number;
  lastError: string | null;
  extractedTitle: string | null;
  createdAt: string;
  finishedAt: string | null;
}

export interface PublicVideoPage {
  video: VideoAsset;
  jsonLd: Record<string, unknown>;
}
