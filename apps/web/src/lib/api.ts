import {
  AnalyticsSummary,
  ApiResult,
  CrawlJob,
  Paginated,
  SessionUser,
  VideoAsset,
  unwrap,
} from "@frame/shared";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8787/api";

type RequestOptions = RequestInit & {
  token?: string;
  next?: { revalidate?: number | false; tags?: string[] };
};

async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  const { token, next, ...rest } = init;
  const headers = new Headers(rest.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers,
    next,
  });

  const json = (await res.json()) as ApiResult<T>;
  return unwrap(json);
}

export function listPublishedVideos(): Promise<Paginated<VideoAsset>> {
  // ISR: revalidate public catalog every 60s
  return request<Paginated<VideoAsset>>("/videos?status=published&pageSize=20", {
    next: { revalidate: 60 },
  });
}

export function getPublicVideo(slug: string): Promise<VideoAsset> {
  return request<VideoAsset>(`/videos/public/${slug}`, {
    next: { revalidate: 30 },
  });
}

export async function login(
  email: string,
  password: string,
): Promise<{ token: string; user: SessionUser }> {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });
}

export function fetchSummary(token: string): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>("/analytics/summary?days=7", {
    token,
    cache: "no-store",
  });
}

export function fetchAllVideos(token: string): Promise<Paginated<VideoAsset>> {
  return request<Paginated<VideoAsset>>("/videos?pageSize=50", {
    token,
    cache: "no-store",
  });
}

export function trackPageView(path: string, videoId?: string): Promise<{ id: number }> {
  const visitorId =
    typeof window !== "undefined"
      ? localStorage.getItem("frame_vid") ??
        (() => {
          const id = `vis_${Math.random().toString(36).slice(2, 10)}`;
          localStorage.setItem("frame_vid", id);
          return id;
        })()
      : "ssr";
  const sessionId =
    typeof window !== "undefined"
      ? sessionStorage.getItem("frame_sid") ??
        (() => {
          const id = `sess_${Math.random().toString(36).slice(2, 10)}`;
          sessionStorage.setItem("frame_sid", id);
          return id;
        })()
      : "ssr";

  return request("/analytics/track", {
    method: "POST",
    body: JSON.stringify({
      name: "page_view",
      path,
      visitorId,
      sessionId,
      videoId,
    }),
    cache: "no-store",
  });
}

export function enqueueCrawl(token: string, url: string): Promise<CrawlJob> {
  return request<CrawlJob>("/crawl", {
    method: "POST",
    token,
    body: JSON.stringify({ url }),
    cache: "no-store",
  });
}

export function listCrawlJobs(token: string): Promise<CrawlJob[]> {
  return request<CrawlJob[]>("/crawl/jobs", { token, cache: "no-store" });
}

export { API_BASE };
