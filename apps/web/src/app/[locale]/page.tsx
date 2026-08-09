import Link from "next/link";
import { notFound } from "next/navigation";
import { listPublishedVideos } from "@/lib/api";
import { isLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/get-dictionary";
import { SiteHeader } from "@/components/SiteHeader";
import styles from "./page.module.css";

export const revalidate = 60;

type Props = { params: Promise<{ locale: string }> };

export default async function HomePage({ params }: Props) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw;
  const dict = await getDictionary(locale);

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

      <div className={styles.mainCol}>
        <SiteHeader locale={locale} dict={dict} />

        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <p className={styles.kicker}>
              <span className={styles.liveDot} /> {dict.home.kicker}
            </p>
            <h1 className={styles.brand}>FRAME</h1>
            <p className={styles.lede}>{dict.home.lede}</p>
            <div className={styles.ctaRow}>
              <Link
                className={styles.ctaPrimary}
                href={
                  videos[0]
                    ? `/${locale}/watch/${videos[0].slug}`
                    : `/${locale}/ops`
                }
              >
                {dict.home.ctaWatch}
              </Link>
              <Link className={styles.ctaGhost} href={`/${locale}/ops`}>
                {dict.home.ctaOps}
              </Link>
              <Link className={styles.ctaGhost} href={`/${locale}/guide`}>
                {dict.home.ctaGuide}
              </Link>
            </div>
          </div>
          <div className={styles.heroVisual} />
        </section>

        <section className={styles.catalog}>
          <header className={styles.catalogHead}>
            <h2>{dict.home.catalogTitle}</h2>
            <p>{dict.home.catalogDesc}</p>
          </header>
          {apiDown ? (
            <p className={styles.warn}>{dict.home.apiDown}</p>
          ) : (
            <ul className={styles.list}>
              {videos.map((v, i) => (
                <li key={v.id} style={{ animationDelay: `${0.08 * i}s` }}>
                  <Link href={`/${locale}/watch/${v.slug}`} className={styles.row}>
                    <span className={styles.idx}>{String(i + 1).padStart(2, "0")}</span>
                    <span className={styles.title}>{v.title}</span>
                    <span className={styles.meta}>
                      {Math.round(v.durationSec / 60)}
                      {dict.home.minutes} · {v.viewCount} {dict.home.views}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
