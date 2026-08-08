import { Inject, Injectable } from "@nestjs/common";
import { Role, SessionUser, isRole } from "@frame/shared";
import { DatabaseService } from "../../db/database.service";

@Injectable()
export class RbacService {
  constructor(@Inject(DatabaseService) private readonly database: DatabaseService) {}

  listUsers(): SessionUser[] {
    const rows = this.database.db
      .prepare(`SELECT id, email, name, role FROM users ORDER BY email`)
      .all() as Array<{ id: string; email: string; name: string; role: string }>;
    return rows.flatMap((r) => {
      if (!isRole(r.role)) return [];
      return [{ id: r.id, email: r.email, name: r.name, role: r.role }];
    });
  }

  setRole(id: string, role: Role): SessionUser | null {
    const result = this.database.db
      .prepare(`UPDATE users SET role = ? WHERE id = ?`)
      .run(role, id);
    if (result.changes === 0) return null;
    const row = this.database.db
      .prepare(`SELECT id, email, name, role FROM users WHERE id = ?`)
      .get(id) as { id: string; email: string; name: string; role: string };
    if (!isRole(row.role)) return null;
    return { id: row.id, email: row.email, name: row.name, role: row.role };
  }
}
