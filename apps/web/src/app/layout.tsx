import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Syne } from "next/font/google";
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

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3088"),
  title: {
    default: "FRAME — Media Ops Console",
    template: "%s · FRAME",
  },
  description:
    "Interview demo: Next.js App Router + NestJS media ops — HLS, RBAC, analytics, chunked upload.",
  openGraph: {
    title: "FRAME",
    description: "Ship video with type-safe ops.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`${syne.variable} ${plex.variable} ${mono.variable}`}>
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
