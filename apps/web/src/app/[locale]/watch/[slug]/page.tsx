import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPublicVideo } from "@/lib/api";
import { TrackView } from "@/components/TrackView";
import { SiteHeader } from "@/components/SiteHeader";
import { isLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/get-dictionary";
import styles from "./watch.module.css";

export const revalidate = 30;

type Props = { params: Promise<{ locale: string; slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale: raw, slug } = await params;
  const dict = isLocale(raw) ? await getDictionary(raw) : null;
  try {
    const video = await getPublicVideo(slug);
    return {
      title: video.title,
      description: video.summary,
      openGraph: {
        title: video.title,
        description: video.summary,
        type: "video.other",
        images: video.posterUrl ? [{ url: video.posterUrl }] : undefined,
      },
    };
  } catch {
    return { title: dict?.watch.notFound ?? "Not found" };
  }
}

export default async function WatchPage({ params }: Props) {
  const { locale: raw, slug } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw;
  const dict = await getDictionary(locale);

  let video;
  try {
    video = await getPublicVideo(slug);
  } catch {
    notFound();
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "VideoObject",
    name: video.title,
    description: video.summary,
    thumbnailUrl: video.posterUrl ? [video.posterUrl] : [],
    uploadDate: video.publishedAt ?? video.createdAt,
    duration: `PT${Math.max(video.durationSec, 1)}S`,
    contentUrl: video.hlsPath,
    inLanguage: locale === "zh" ? "zh-CN" : "en",
  };

  return (
    <main className={styles.page}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <TrackView path={`/${locale}/watch/${slug}`} videoId={video.id} />
      <SiteHeader locale={locale} dict={dict} />

      <div className={styles.stage}>
        <div
          className={styles.poster}
          style={
            video.posterUrl
              ? { backgroundImage: `url(${video.posterUrl})` }
              : undefined
          }
        >
          <div className={styles.overlay}>
            <p className={styles.hls}>
              {dict.watch.hls} · <code>/api/videos/{video.id}/hls/master.m3u8</code>
            </p>
            <h1>{video.title}</h1>
            <p className={styles.summary}>{video.summary}</p>
            <p className={styles.meta}>
              {dict.watch.meta.replace("{views}", String(video.viewCount))}
            </p>
            <p className={styles.back}>
              <Link href={`/${locale}/guide`}>{dict.nav.guide}</Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
