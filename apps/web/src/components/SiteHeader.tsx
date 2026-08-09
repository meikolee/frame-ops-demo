import Link from "next/link";
import type { Locale } from "@/i18n/config";
import type { Dictionary } from "@/i18n/get-dictionary";
import { LocaleSwitcher } from "./LocaleSwitcher";
import styles from "./SiteHeader.module.css";

export function SiteHeader({
  locale,
  dict,
  variant = "default",
}: {
  locale: Locale;
  dict: Dictionary;
  variant?: "default" | "minimal";
}) {
  return (
    <header className={styles.header} data-variant={variant}>
      <nav className={styles.nav}>
        <Link href={`/${locale}`} className={styles.brand}>
          FRAME
        </Link>
        <div className={styles.links}>
          <Link href={`/${locale}/guide`}>{dict.nav.guide}</Link>
          <Link href={`/${locale}/ops`}>{dict.nav.ops}</Link>
          <LocaleSwitcher
            locale={locale}
            label={dict.lang.label}
            labels={{ zh: dict.lang.zh, en: dict.lang.en }}
          />
        </div>
      </nav>
    </header>
  );
}
