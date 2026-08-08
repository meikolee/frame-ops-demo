import { Inject, Injectable } from "@nestjs/common";
import { Paginated, VideoAsset, VideoStatus } from "@frame/shared";
import { DatabaseService } from "../../db/database.service";

interface VideoRow {
  id: string;
  slug: string;
  title: string;
  summary: string;
  status: string;
  duration_sec: number;
  hls_path: string | null;
  poster_url: string | null;
  view_count: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

function mapVideo(row: VideoRow): VideoAsset {
  return {
    id: row.id,
    slug: row.slug,
    title: row.title,
    summary: row.summary,
    status: row.status as VideoStatus,
    durationSec: row.duration_sec,
    hlsPath: row.hls_path,
    posterUrl: row.poster_url,
    viewCount: row.view_count,
    publishedAt: row.published_at,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

@Injectable()
export class VideosService {
  constructor(@Inject(DatabaseService) private readonly database: DatabaseService) {}

  list(page: number, pageSize: number, status?: VideoStatus): Paginated<VideoAsset> {
    const offset = (Math.max(page, 1) - 1) * pageSize;
    const where = status ? "WHERE status = ?" : "";
    const params = status ? [status] : [];
    const total = (
      this.database.db.prepare(`SELECT COUNT(*) AS c FROM videos ${where}`).get(...params) as {
        c: number;
      }
    ).c;
    const rows = this.database.db
      .prepare(
        `SELECT * FROM videos ${where}
         ORDER BY COALESCE(published_at, created_at) DESC
         LIMIT ? OFFSET ?`,
      )
      .all(...params, pageSize, offset) as VideoRow[];
    return { items: rows.map(mapVideo), total, page, pageSize };
  }

  findBySlug(slug: string): VideoAsset | null {
    const row = this.database.db
      .prepare(`SELECT * FROM videos WHERE slug = ?`)
      .get(slug) as VideoRow | undefined;
    return row ? mapVideo(row) : null;
  }

  create(title: string, summary: string): VideoAsset {
    const id = DatabaseService.newId("v");
    const slug = `${slugify(title) || "video"}-${id.slice(-4)}`;
    const now = new Date().toISOString();
    this.database.db
      .prepare(
        `INSERT INTO videos (id, slug, title, summary, status, duration_sec, created_at, updated_at)
         VALUES (?, ?, ?, ?, 'draft', 0, ?, ?)`,
      )
      .run(id, slug, title, summary, now, now);
    return this.findBySlug(slug)!;
  }

  updateStatus(id: string, status: VideoStatus): VideoAsset | null {
    const publishedAt = status === "published" ? new Date().toISOString() : null;
    const result = this.database.db
      .prepare(
        `UPDATE videos
         SET status = ?, published_at = COALESCE(?, published_at), updated_at = ?
         WHERE id = ?`,
      )
      .run(status, publishedAt, new Date().toISOString(), id);
    if (result.changes === 0) return null;
    const row = this.database.db
      .prepare(`SELECT * FROM videos WHERE id = ?`)
      .get(id) as VideoRow;
    return mapVideo(row);
  }

  buildHlsMaster(id: string): string {
    // Multi-bitrate master — interview: ABR ladder + CDN origin path convention.
    return `#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360
/media/${id}/360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720
/media/${id}/720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5500000,RESOLUTION=1920x1080
/media/${id}/1080p.m3u8
`;
  }
}
