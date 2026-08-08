import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPublicVideo } from "@/lib/api";
import { TrackView } from "@/components/TrackView";
import styles from "./watch.module.css";

export const revalidate = 30;

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
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
    return { title: "Not found" };
  }
}

export default async function WatchPage({ params }: Props) {
  const { slug } = await params;
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
  };

  return (
    <main className={styles.page}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <TrackView path={`/watch/${slug}`} videoId={video.id} />

      <nav className={styles.nav}>
        <Link href="/">FRAME</Link>
        <Link href="/ops">Ops</Link>
      </nav>

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
              HLS master · <code>/api/videos/{video.id}/hls/master.m3u8</code>
            </p>
            <h1>{video.title}</h1>
            <p className={styles.summary}>{video.summary}</p>
            <p className={styles.meta}>
              SSR detail · ISR 30s · JSON-LD VideoObject · {video.viewCount} recorded views
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
