import { listPublishedVideos } from "@/lib/api";
import { locales } from "@/i18n/config";

export const revalidate = 3600;

export default async function sitemap() {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3088";

  const staticPaths = ["", "/ops", "/guide"];
  const staticRoutes = locales.flatMap((locale) =>
    staticPaths.map((path) => ({
      url: `${base}/${locale}${path}`,
      lastModified: new Date(),
      changeFrequency: "weekly" as const,
      priority: path === "" ? 1 : path === "/guide" ? 0.9 : 0.4,
    })),
  );

  try {
    const { items } = await listPublishedVideos();
    const videoRoutes = locales.flatMap((locale) =>
      items.map((v) => ({
        url: `${base}/${locale}/watch/${v.slug}`,
        lastModified: new Date(v.updatedAt),
        changeFrequency: "daily" as const,
        priority: 0.8,
      })),
    );
    return [...staticRoutes, ...videoRoutes];
  } catch {
    return staticRoutes;
  }
}
