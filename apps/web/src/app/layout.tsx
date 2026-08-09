import { cookies } from "next/headers";
import { IBM_Plex_Mono, IBM_Plex_Sans, Syne } from "next/font/google";
import { isLocale } from "@/i18n/config";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["500", "700", "800"],
});

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-plex",
  weight: ["400", "500", "600"],
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieLocale = (await cookies()).get("NEXT_LOCALE")?.value;
  const locale = cookieLocale && isLocale(cookieLocale) ? cookieLocale : "zh";
  const htmlLang = locale === "en" ? "en" : "zh-CN";

  return (
    <html
      lang={htmlLang}
      className={`${syne.variable} ${plex.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <body
        style={{
          fontFamily: "var(--font-plex), var(--font-body)",
          ["--font-display" as string]: "var(--font-syne), Syne, sans-serif",
          ["--font-mono" as string]: "var(--font-mono), 'IBM Plex Mono', monospace",
        }}
      >
        {children}
      </body>
    </html>
  );
}
