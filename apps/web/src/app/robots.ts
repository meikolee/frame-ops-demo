import type { MetadataRoute } from "next";
import { locales } from "@/i18n/config";

export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3088";
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: locales.map((l) => `/${l}/ops`),
    },
    sitemap: `${base}/sitemap.xml`,
  };
}
