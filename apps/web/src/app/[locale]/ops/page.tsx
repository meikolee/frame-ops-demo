import { notFound } from "next/navigation";
import { isLocale } from "@/i18n/config";
import { getDictionary } from "@/i18n/get-dictionary";
import { SiteHeader } from "@/components/SiteHeader";
import { OpsConsole } from "@/components/OpsConsole";
import styles from "@/components/OpsConsole.module.css";

type Props = { params: Promise<{ locale: string }> };

export default async function OpsPage({ params }: Props) {
  const { locale: raw } = await params;
  if (!isLocale(raw)) notFound();
  const locale = raw;
  const dict = await getDictionary(locale);

  return (
    <main className={styles.shell}>
      <SiteHeader locale={locale} dict={dict} />
      <OpsConsole locale={locale} dict={dict} />
    </main>
  );
}
