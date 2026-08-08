import { Body, Controller, Get, Inject, Param, Patch, UseGuards } from "@nestjs/common";
import { IsIn } from "class-validator";
import { ApiResult, Role, SessionUser, fail, ok } from "@frame/shared";
import { RbacService } from "./rbac.service";
import {
  AuthGuard,
  PermissionsGuard,
  RequirePermissions,
} from "../../common/guards/auth.guards";

class RoleDto {
  @IsIn(["viewer", "editor", "admin"])
  role!: Role;
}

@Controller("rbac")
@UseGuards(AuthGuard, PermissionsGuard)
export class RbacController {
  constructor(@Inject(RbacService) private readonly rbac: RbacService) {}

  @Get("users")
  @RequirePermissions("rbac:manage")
  users(): ApiResult<SessionUser[]> {
    return ok(this.rbac.listUsers());
  }

  @Patch("users/:id/role")
  @RequirePermissions("rbac:manage")
  setRole(
    @Param("id") id: string,
    @Body() body: RoleDto,
  ): ApiResult<SessionUser> {
    const user = this.rbac.setRole(id, body.role);
    if (!user) return fail("NOT_FOUND", "User not found");
    return ok(user);
  }
}
