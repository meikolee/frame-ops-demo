import { Inject, Injectable } from "@nestjs/common";
import { AnalyticsEventInput, AnalyticsSummary } from "@frame/shared";
import { DatabaseService } from "../../db/database.service";

@Injectable()
export class AnalyticsService {
  constructor(@Inject(DatabaseService) private readonly database: DatabaseService) {}

  track(input: AnalyticsEventInput): { id: number } {
    const result = this.database.db
      .prepare(
        `INSERT INTO analytics_events (name, path, visitor_id, session_id, video_id, meta_json)
         VALUES (?, ?, ?, ?, ?, ?)`,
      )
      .run(
        input.name,
        input.path,
        input.visitorId,
        input.sessionId,
        input.videoId ?? null,
        input.meta ? JSON.stringify(input.meta) : null,
      );
    return { id: Number(result.lastInsertRowid) };
  }

  /**
   * Metric definitions (interview):
   * - PV: count of page_view events in window
   * - UV: DISTINCT visitor_id with page_view in window
   * - D1 retention: share of day0 visitors who also appear on day0+1
   */
  summary(days: number): AnalyticsSummary {
    const since = new Date();
    since.setDate(since.getDate() - Math.max(days, 1));
    const sinceIso = since.toISOString();

    const pv = (
      this.database.db
        .prepare(
          `SELECT COUNT(*) AS c FROM analytics_events
           WHERE name = 'page_view' AND created_at >= ?`,
        )
        .get(sinceIso) as { c: number }
    ).c;

    const uv = (
      this.database.db
        .prepare(
          `SELECT COUNT(DISTINCT visitor_id) AS c FROM analytics_events
           WHERE name = 'page_view' AND created_at >= ?`,
        )
        .get(sinceIso) as { c: number }
    ).c;

    const plays = (
      this.database.db
        .prepare(
          `SELECT COUNT(*) AS c FROM analytics_events
           WHERE name = 'video_play' AND created_at >= ?`,
        )
        .get(sinceIso) as { c: number }
    ).c;

    const completes = (
      this.database.db
        .prepare(
          `SELECT COUNT(*) AS c FROM analytics_events
           WHERE name = 'video_complete' AND created_at >= ?`,
        )
        .get(sinceIso) as { c: number }
    ).c;

    const day0 = new Date();
    day0.setDate(day0.getDate() - 1);
    const day0Start = new Date(day0);
    day0Start.setHours(0, 0, 0, 0);
    const day0End = new Date(day0);
    day0End.setHours(23, 59, 59, 999);
    const day1Start = new Date(day0Start);
    day1Start.setDate(day1Start.getDate() + 1);
    const day1End = new Date(day0End);
    day1End.setDate(day1End.getDate() + 1);

    const cohort = (
      this.database.db
        .prepare(
          `SELECT COUNT(DISTINCT visitor_id) AS c FROM analytics_events
           WHERE name = 'page_view' AND created_at BETWEEN ? AND ?`,
        )
        .get(day0Start.toISOString(), day0End.toISOString()) as { c: number }
    ).c;

    const returned = (
      this.database.db
        .prepare(
          `SELECT COUNT(DISTINCT a.visitor_id) AS c
           FROM analytics_events a
           WHERE a.name = 'page_view'
             AND a.created_at BETWEEN ? AND ?
             AND EXISTS (
               SELECT 1 FROM analytics_events b
               WHERE b.visitor_id = a.visitor_id
                 AND b.name = 'page_view'
                 AND b.created_at BETWEEN ? AND ?
             )`,
        )
        .get(
          day0Start.toISOString(),
          day0End.toISOString(),
          day1Start.toISOString(),
          day1End.toISOString(),
        ) as { c: number }
    ).c;

    const d1Retention = cohort === 0 ? 0 : Number((returned / cohort).toFixed(4));

    return { pv, uv, d1Retention, plays, completes };
  }
}
