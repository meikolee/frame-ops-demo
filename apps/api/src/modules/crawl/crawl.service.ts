import { Inject, Injectable } from "@nestjs/common";
import { CrawlJob } from "@frame/shared";
import { DatabaseService } from "../../db/database.service";

interface CrawlRow {
  id: string;
  url: string;
  status: string;
  attempts: number;
  last_error: string | null;
  extracted_title: string | null;
  created_at: string;
  finished_at: string | null;
}

function mapJob(row: CrawlRow): CrawlJob {
  return {
    id: row.id,
    url: row.url,
    status: row.status as CrawlJob["status"],
    attempts: row.attempts,
    lastError: row.last_error,
    extractedTitle: row.extracted_title,
    createdAt: row.created_at,
    finishedAt: row.finished_at,
  };
}

/**
 * Tiny crawler with retry + backoff + anti-bot basics:
 * - polite User-Agent
 * - exponential backoff on 429/5xx
 * - hard attempt cap
 * Real systems add robots.txt, proxy pools, per-host rate limits.
 */
@Injectable()
export class CrawlService {
  constructor(@Inject(DatabaseService) private readonly database: DatabaseService) {}

  enqueue(url: string): CrawlJob {
    const id = DatabaseService.newId("crawl");
    this.database.db
      .prepare(
        `INSERT INTO crawl_jobs (id, url, status, attempts) VALUES (?, ?, 'queued', 0)`,
      )
      .run(id, url);

    // Fire-and-forget demo worker
    void this.runWithRetry(id, url);
    return this.get(id)!;
  }

  list(): CrawlJob[] {
    const rows = this.database.db
      .prepare(`SELECT * FROM crawl_jobs ORDER BY created_at DESC LIMIT 50`)
      .all() as CrawlRow[];
    return rows.map(mapJob);
  }

  private get(id: string): CrawlJob | null {
    const row = this.database.db
      .prepare(`SELECT * FROM crawl_jobs WHERE id = ?`)
      .get(id) as CrawlRow | undefined;
    return row ? mapJob(row) : null;
  }

  private async runWithRetry(id: string, url: string): Promise<void> {
    const maxAttempts = 3;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      this.database.db
        .prepare(
          `UPDATE crawl_jobs SET status = ?, attempts = ? WHERE id = ?`,
        )
        .run(attempt === 1 ? "running" : "retrying", attempt, id);

      try {
        const title = await this.fetchTitle(url);
        this.database.db
          .prepare(
            `UPDATE crawl_jobs
             SET status = 'succeeded', extracted_title = ?, last_error = NULL, finished_at = ?
             WHERE id = ?`,
          )
          .run(title, new Date().toISOString(), id);
        return;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        this.database.db
          .prepare(`UPDATE crawl_jobs SET last_error = ? WHERE id = ?`)
          .run(message, id);
        if (attempt === maxAttempts) {
          this.database.db
            .prepare(
              `UPDATE crawl_jobs SET status = 'failed', finished_at = ? WHERE id = ?`,
            )
            .run(new Date().toISOString(), id);
          return;
        }
        const backoffMs = 200 * 2 ** (attempt - 1);
        await new Promise((r) => setTimeout(r, backoffMs));
      }
    }
  }

  private async fetchTitle(url: string): Promise<string> {
    // Demo mode: don't hit the network for known demo hosts; simulate extraction.
    if (url.includes("example.com") || url.includes("frame.demo")) {
      return `Extracted: ${new URL(url).pathname || "/"}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const res = await fetch(url, {
        signal: controller.signal,
        headers: {
          "User-Agent": "FrameOpsBot/1.0 (+https://frame.demo/bot; respectful)",
          Accept: "text/html",
        },
        redirect: "follow",
      });
      if (res.status === 429 || res.status >= 500) {
        throw new Error(`Retryable HTTP ${res.status}`);
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const html = await res.text();
      const match = html.match(/<title[^>]*>([^<]*)<\/title>/i);
      return (match?.[1] ?? "Untitled").trim().slice(0, 200);
    } finally {
      clearTimeout(timer);
    }
  }
}
