import { Inject, Injectable } from "@nestjs/common";
import { SessionUser, isRole } from "@frame/shared";
import { DatabaseService } from "../../db/database.service";

interface UserRow {
  id: string;
  email: string;
  name: string;
  password_hash: string;
  role: string;
}

@Injectable()
export class AuthService {
  constructor(@Inject(DatabaseService) private readonly database: DatabaseService) {}

  validate(email: string, password: string): SessionUser | null {
    const row = this.database.db
      .prepare(`SELECT id, email, name, password_hash, role FROM users WHERE email = ?`)
      .get(email) as UserRow | undefined;
    if (!row) return null;
    if (row.password_hash !== DatabaseService.hashPassword(password)) return null;
    if (!isRole(row.role)) return null;
    return { id: row.id, email: row.email, name: row.name, role: row.role };
  }
}
