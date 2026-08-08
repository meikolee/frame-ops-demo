import { listPublishedVideos } from "@/lib/api";

export const revalidate = 3600;

export default async function sitemap() {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3088";
  const staticRoutes = ["", "/ops"].map((path) => ({
    url: `${base}${path}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: path === "" ? 1 : 0.4,
  }));

  try {
    const { items } = await listPublishedVideos();
    const videoRoutes = items.map((v) => ({
      url: `${base}/watch/${v.slug}`,
      lastModified: new Date(v.updatedAt),
      changeFrequency: "daily" as const,
      priority: 0.8,
    }));
    return [...staticRoutes, ...videoRoutes];
  } catch {
    return staticRoutes;
  }
}
