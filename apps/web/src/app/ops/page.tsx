"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import {
  AnalyticsSummary,
  CrawlJob,
  SessionUser,
  VideoAsset,
  permissionsFor,
} from "@frame/shared";
import {
  enqueueCrawl,
  fetchAllVideos,
  fetchSummary,
  listCrawlJobs,
  login,
} from "@/lib/api";
import styles from "./ops.module.css";

type AuthState = { token: string; user: SessionUser };

export default function OpsPage() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [email, setEmail] = useState("admin@frame.demo");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [videos, setVideos] = useState<VideoAsset[]>([]);
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [crawlUrl, setCrawlUrl] = useState("https://example.com/frame-demo");
  const [busy, setBusy] = useState(false);

  const perms = useMemo(
    () => (auth ? permissionsFor(auth.user.role) : []),
    [auth],
  );

  async function refresh(token: string) {
    const [s, v, j] = await Promise.all([
      fetchSummary(token),
      fetchAllVideos(token),
      listCrawlJobs(token).catch(() => [] as CrawlJob[]),
    ]);
    setSummary(s);
    setVideos(v.items);
    setJobs(j);
  }

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await login(email, password);
      setAuth(result);
      await refresh(result.token);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onCrawl(e: FormEvent) {
    e.preventDefault();
    if (!auth) return;
    setBusy(true);
    try {
      await enqueueCrawl(auth.token, crawlUrl);
      await new Promise((r) => setTimeout(r, 600));
      setJobs(await listCrawlJobs(auth.token));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={styles.shell}>
      <header className={styles.top}>
        <Link href="/" className={styles.brand}>
          FRAME
        </Link>
        <span className={styles.tag}>CSR ops console · client components</span>
      </header>

      {!auth ? (
        <form className={styles.login} onSubmit={onLogin}>
          <h1>Sign in</h1>
          <p>Demo accounts: admin / editor / viewer @frame.demo — passwords `*123`.</p>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error ? <p className={styles.error}>{error}</p> : null}
          <button type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Enter control room"}
          </button>
        </form>
      ) : (
        <div className={styles.grid}>
          <section className={styles.panel}>
            <h2>Session</h2>
            <p className={styles.mono}>
              {auth.user.name} · {auth.user.role}
            </p>
            <ul className={styles.permList}>
              {perms.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </section>

          <section className={styles.panel}>
            <h2>Analytics (7d)</h2>
            {summary ? (
              <dl className={styles.metrics}>
                <div>
                  <dt>PV</dt>
                  <dd>{summary.pv}</dd>
                </div>
                <div>
                  <dt>UV</dt>
                  <dd>{summary.uv}</dd>
                </div>
                <div>
                  <dt>D1</dt>
                  <dd>{(summary.d1Retention * 100).toFixed(1)}%</dd>
                </div>
                <div>
                  <dt>Plays</dt>
                  <dd>{summary.plays}</dd>
                </div>
              </dl>
            ) : (
              <p className={styles.mono}>No data</p>
            )}
            <p className={styles.hint}>
              PV = page_view rows · UV = distinct visitor_id · D1 = cohort return rate
            </p>
          </section>

          <section className={styles.panelWide}>
            <h2>Videos</h2>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Slug</th>
                </tr>
              </thead>
              <tbody>
                {videos.map((v) => (
                  <tr key={v.id}>
                    <td>{v.title}</td>
                    <td>
                      <span data-status={v.status}>{v.status}</span>
                    </td>
                    <td className={styles.mono}>
                      <Link href={`/watch/${v.slug}`}>{v.slug}</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className={styles.panelWide}>
            <h2>Crawl job</h2>
            <form className={styles.crawl} onSubmit={onCrawl}>
              <input
                value={crawlUrl}
                onChange={(e) => setCrawlUrl(e.target.value)}
                placeholder="https://..."
              />
              <button type="submit" disabled={busy || !perms.includes("crawl:run")}>
                Enqueue
              </button>
            </form>
            <ul className={styles.jobs}>
              {jobs.map((j) => (
                <li key={j.id}>
                  <span data-status={j.status}>{j.status}</span>
                  <span className={styles.mono}>{j.url}</span>
                  <span>{j.extractedTitle ?? j.lastError ?? "—"}</span>
                </li>
              ))}
            </ul>
          </section>

          {error ? <p className={styles.error}>{error}</p> : null}
        </div>
      )}
    </main>
  );
}
