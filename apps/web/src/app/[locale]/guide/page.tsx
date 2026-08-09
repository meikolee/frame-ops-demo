import { notFound } from "next/navigation";
import { isLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/get-dictionary";
import { SiteHeader } from "@/components/SiteHeader";
import styles from "./guide.module.css";

type Props = { params: Promise<{ locale: string }> };

export default async function GuidePage({ params }: Props) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw;
  const dict = await getDictionary(locale);
  const g = dict.guide;

  return (
    <main className={styles.page}>
      <SiteHeader locale={locale} dict={dict} />
      <div className={styles.layout}>
        <aside className={styles.toc}>
          <p className={styles.tocTitle}>{g.toc}</p>
          <ol>
            {g.sections.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`}>{s.title}</a>
              </li>
            ))}
          </ol>
        </aside>

        <article className={styles.article}>
          <header className={styles.hero}>
            <p className={styles.kicker}>FRAME / GUIDE</p>
            <h1>{g.title}</h1>
            <p className={styles.subtitle}>{g.subtitle}</p>
          </header>

          {g.sections.map((section, index) => (
            <section
              key={section.id}
              id={section.id}
              className={styles.section}
              style={{ animationDelay: `${0.05 * index}s` }}
            >
              <h2>{section.title}</h2>
              <div className={styles.body}>
                {section.body.map((line) => {
                  const isCode =
                    /^(npm |GET |POST |EXPLAIN|Invoke-|deploy\/|Token |revalidate|①)/.test(
                      line,
                    ) ||
                    line.startsWith("http") ||
                    line.includes("→");
                  return isCode ? (
                    <pre key={line} className={styles.code}>
                      {line}
                    </pre>
                  ) : (
                    <p key={line}>{line}</p>
                  );
                })}
              </div>
            </section>
          ))}
        </article>
      </div>
    </main>
  );
}
