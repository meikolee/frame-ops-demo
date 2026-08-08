import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { Injectable, OnModuleInit } from "@nestjs/common";
import { createHash, randomBytes } from "node:crypto";

function hashPassword(password: string): string {
  return createHash("sha256").update(`frame:${password}`).digest("hex");
}

@Injectable()
export class DatabaseService implements OnModuleInit {
  readonly db: Database.Database;

  constructor() {
    const dataDir = path.resolve(process.cwd(), "data");
    fs.mkdirSync(dataDir, { recursive: true });
    const dbPath = path.join(dataDir, "frame.sqlite");
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
  }

  onModuleInit(): void {
    const schemaPath = path.resolve(__dirname, "../../../../sql/schema.sql");
    const fallback = path.resolve(process.cwd(), "../../sql/schema.sql");
    const file = fs.existsSync(schemaPath) ? schemaPath : fallback;
    const sql = fs.readFileSync(file, "utf8");
    this.db.exec(sql);
    this.seed();
  }

  private seed(): void {
    const count = this.db.prepare("SELECT COUNT(*) AS c FROM users").get() as { c: number };
    if (count.c > 0) return;

    const insertUser = this.db.prepare(
      `INSERT INTO users (id, email, name, password_hash, role) VALUES (?, ?, ?, ?, ?)`,
    );
    const users = [
      ["u_admin", "admin@frame.demo", "Ada Admin", hashPassword("admin123"), "admin"],
      ["u_editor", "editor@frame.demo", "Ed Editor", hashPassword("editor123"), "editor"],
      ["u_viewer", "viewer@frame.demo", "Vi Viewer", hashPassword("viewer123"), "viewer"],
    ] as const;

    const insertVideo = this.db.prepare(
      `INSERT INTO videos
        (id, slug, title, summary, status, duration_sec, hls_path, poster_url, view_count, published_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    );

    const now = new Date().toISOString();
    const videos = [
      [
        "v_aurora",
        "aurora-cutdown",
        "Aurora Cutdown - Night Ops Reel",
        "A 90-second cutdown demonstrating HLS packaging, CDN cache keys, and poster generation.",
        "published",
        92,
        "/media/aurora/master.m3u8",
        "https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?w=1600&q=80",
        1280,
        now,
      ],
      [
        "v_lathe",
        "lathe-room-walkthrough",
        "Lathe Room Walkthrough",
        "Industrial floor tour - used for SEO SSR + structured data demo.",
        "published",
        184,
        "/media/lathe/master.m3u8",
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=1600&q=80",
        640,
        now,
      ],
      [
        "v_draft",
        "untitled-draft",
        "Untitled Draft",
        "Still processing in the transcoder queue.",
        "processing",
        0,
        null,
        null,
        0,
        null,
      ],
    ] as const;

    const tx = this.db.transaction(() => {
      for (const u of users) insertUser.run(...u);
      for (const v of videos) insertVideo.run(...v);

      const insertEvent = this.db.prepare(
        `INSERT INTO analytics_events (name, path, visitor_id, session_id, video_id, created_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
      );
      for (let i = 0; i < 40; i++) {
        const dayOffset = i % 3;
        const d = new Date();
        d.setDate(d.getDate() - dayOffset);
        insertEvent.run(
          "page_view",
          i % 2 === 0 ? "/watch/aurora-cutdown" : "/watch/lathe-room-walkthrough",
          `vis_${i % 12}`,
          `sess_${i}`,
          i % 2 === 0 ? "v_aurora" : "v_lathe",
          d.toISOString(),
        );
      }
    });
    tx();
  }

  static hashPassword(password: string): string {
    return hashPassword(password);
  }

  static newId(prefix: string): string {
    return `${prefix}_${randomBytes(6).toString("hex")}`;
  }
}
