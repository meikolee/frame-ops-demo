import { Inject, Injectable } from "@nestjs/common";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { ChunkInitRequest, ChunkInitResponse } from "@frame/shared";
import { DatabaseService } from "../../db/database.service";

interface UploadRow {
  id: string;
  object_key: string;
  chunk_size: number;
  total_chunks: number;
  received_mask: string;
  status: string;
}

/**
 * Multipart / resumable upload against local "object storage" root.
 * Swap `storageRoot` writes for S3/R2/OSS PutObject + CompleteMultipartUpload.
 */
@Injectable()
export class UploadService {
  private readonly storageRoot: string;

  constructor(@Inject(DatabaseService) private readonly database: DatabaseService) {
    this.storageRoot = path.resolve(process.cwd(), "data", "objects");
    fs.mkdirSync(this.storageRoot, { recursive: true });
  }

  init(input: ChunkInitRequest, userId: string): ChunkInitResponse {
    const uploadId = DatabaseService.newId("up");
    const totalChunks = Math.ceil(input.sizeBytes / input.chunkSize);
    const key = `uploads/${new Date().toISOString().slice(0, 10)}/${uploadId}-${input.filename}`;
    const mask = "0".repeat(totalChunks);
    this.database.db
      .prepare(
        `INSERT INTO uploads
          (id, object_key, filename, mime_type, size_bytes, chunk_size, total_chunks, received_mask, status, created_by)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)`,
      )
      .run(
        uploadId,
        key,
        input.filename,
        input.mimeType,
        input.sizeBytes,
        input.chunkSize,
        totalChunks,
        mask,
        userId,
      );
    fs.mkdirSync(path.join(this.storageRoot, uploadId), { recursive: true });
    return { uploadId, key, chunkSize: input.chunkSize, totalChunks };
  }

  receiveChunk(
    uploadId: string,
    index: number,
    buffer: Buffer,
  ): { received: number; total: number } | null {
    const row = this.database.db
      .prepare(`SELECT * FROM uploads WHERE id = ?`)
      .get(uploadId) as UploadRow | undefined;
    if (!row) return null;
    if (index < 0 || index >= row.total_chunks) {
      throw new Error("chunk index out of range");
    }
    const chunkPath = path.join(this.storageRoot, uploadId, `${index}.part`);
    fs.writeFileSync(chunkPath, buffer);
    const mask = row.received_mask.split("");
    mask[index] = "1";
    const next = mask.join("");
    this.database.db
      .prepare(`UPDATE uploads SET received_mask = ? WHERE id = ?`)
      .run(next, uploadId);
    return {
      received: next.split("").filter((c) => c === "1").length,
      total: row.total_chunks,
    };
  }

  complete(
    uploadId: string,
  ):
    | { ok: true; data: { key: string; etag: string } }
    | { ok: false; code: string; message: string } {
    const row = this.database.db
      .prepare(`SELECT * FROM uploads WHERE id = ?`)
      .get(uploadId) as UploadRow | undefined;
    if (!row) return { ok: false, code: "NOT_FOUND", message: "Upload not found" };
    if (row.received_mask.includes("0")) {
      return { ok: false, code: "INCOMPLETE", message: "Not all chunks received" };
    }

    // Transaction: assemble object + mark complete atomically from DB POV.
    const assemble = this.database.db.transaction(() => {
      this.database.db
        .prepare(`UPDATE uploads SET status = 'assembling' WHERE id = ?`)
        .run(uploadId);

      const finalPath = path.join(this.storageRoot, row.object_key);
      fs.mkdirSync(path.dirname(finalPath), { recursive: true });
      const parts: Buffer[] = [];
      const hash = createHash("md5");
      for (let i = 0; i < row.total_chunks; i++) {
        const part = fs.readFileSync(path.join(this.storageRoot, uploadId, `${i}.part`));
        parts.push(part);
        hash.update(part);
      }
      fs.writeFileSync(finalPath, Buffer.concat(parts));

      this.database.db
        .prepare(
          `UPDATE uploads SET status = 'complete', completed_at = ? WHERE id = ?`,
        )
        .run(new Date().toISOString(), uploadId);

      return { key: row.object_key, etag: hash.digest("hex") };
    });

    return { ok: true, data: assemble() };
  }
}
