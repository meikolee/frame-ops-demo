import Link from "next/link";
import { listPublishedVideos } from "@/lib/api";
import styles from "./page.module.css";

export const revalidate = 60;

export default async function HomePage() {
  let videos: Awaited<ReturnType<typeof listPublishedVideos>>["items"] = [];
  let apiDown = false;
  try {
    const page = await listPublishedVideos();
    videos = page.items;
  } catch {
    apiDown = true;
  }

  return (
    <main className={styles.shell}>
      <aside className={styles.rail} aria-hidden>
        <span className={styles.railMark}>FRAME</span>
        <span className={styles.railMeta}>OPS / 01</span>
      </aside>

      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={styles.kicker}>
            <span className={styles.liveDot} /> MEDIA CONTROL ROOM
          </p>
          <h1 className={styles.brand}>FRAME</h1>
          <p className={styles.lede}>
            Type-safe media ops — NestJS guards, App Router boundaries, SQL indexes, and deploy
            playbooks in one runnable demo.
          </p>
          <div className={styles.ctaRow}>
            <Link className={styles.ctaPrimary} href={videos[0] ? `/watch/${videos[0].slug}` : "/ops"}>
              Watch published reel
            </Link>
            <Link className={styles.ctaGhost} href="/ops">
              Open ops console
            </Link>
          </div>
        </div>
        <div className={styles.heroVisual} />
      </section>

      <section className={styles.catalog}>
        <header className={styles.catalogHead}>
          <h2>Published catalog</h2>
          <p>SSR + ISR (revalidate 60s). Structured data lives on each watch page.</p>
        </header>
        {apiDown ? (
          <p className={styles.warn}>API offline — start `@frame/api` on :8787</p>
        ) : (
          <ul className={styles.list}>
            {videos.map((v, i) => (
              <li key={v.id} style={{ animationDelay: `${0.08 * i}s` }}>
                <Link href={`/watch/${v.slug}`} className={styles.row}>
                  <span className={styles.idx}>{String(i + 1).padStart(2, "0")}</span>
                  <span className={styles.title}>{v.title}</span>
                  <span className={styles.meta}>
                    {Math.round(v.durationSec / 60)}m · {v.viewCount} views
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
