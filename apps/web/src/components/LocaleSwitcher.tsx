"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Locale } from "@/i18n/config";
import { locales } from "@/i18n/config";
import styles from "./LocaleSwitcher.module.css";

export function LocaleSwitcher({
  locale,
  label,
  labels,
}: {
  locale: Locale;
  label: string;
  labels: Record<Locale, string>;
}) {
  const pathname = usePathname() || "/";
  const rest = pathname.replace(/^\/(zh|en)(?=\/|$)/, "") || "";

  return (
    <div className={styles.wrap} aria-label={label}>
      {locales.map((l) => (
        <Link
          key={l}
          href={`/${l}${rest}`}
          className={l === locale ? styles.active : styles.item}
          hrefLang={l}
          lang={l}
        >
          {labels[l]}
        </Link>
      ))}
    </div>
  );
}
