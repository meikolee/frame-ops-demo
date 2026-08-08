import {
  CanActivate,
  ExecutionContext,
  Inject,
  Injectable,
  SetMetadata,
  UnauthorizedException,
  ForbiddenException,
} from "@nestjs/common";
import { Reflector } from "@nestjs/core";
import {
  Permission,
  Role,
  SessionUser,
  hasPermission,
  isRole,
} from "@frame/shared";
import { Request } from "express";

export const PERMISSIONS_KEY = "permissions";
export const RequirePermissions = (...permissions: Permission[]) =>
  SetMetadata(PERMISSIONS_KEY, permissions);

export type AuthedRequest = Request & { user?: SessionUser };

/** Demo auth: `Authorization: Bearer <role>:<userId>` e.g. Bearer admin:u_admin */
@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest<AuthedRequest>();
    const header = req.headers.authorization;
    if (!header?.startsWith("Bearer ")) {
      throw new UnauthorizedException("Missing Bearer token");
    }
    const token = header.slice("Bearer ".length).trim();
    const [roleRaw, userId, ...rest] = token.split(":");
    if (!userId || rest.length > 0 || !isRole(roleRaw)) {
      throw new UnauthorizedException("Malformed token — use role:userId");
    }
    const role: Role = roleRaw;
    req.user = {
      id: userId,
      email: `${role}@frame.demo`,
      name: role,
      role,
    };
    return true;
  }
}

@Injectable()
export class PermissionsGuard implements CanActivate {
  constructor(@Inject(Reflector) private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<Permission[] | undefined>(
      PERMISSIONS_KEY,
      [context.getHandler(), context.getClass()],
    );
    if (!required || required.length === 0) return true;

    const req = context.switchToHttp().getRequest<AuthedRequest>();
    const user = req.user;
    if (!user) throw new UnauthorizedException();

    const missing = required.filter((p) => !hasPermission(user.role, p));
    if (missing.length > 0) {
      throw new ForbiddenException(`Missing permissions: ${missing.join(", ")}`);
    }
    return true;
  }
}
