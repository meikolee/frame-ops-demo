import { createParamDecorator, ExecutionContext } from "@nestjs/common";
import { SessionUser } from "@frame/shared";
import { AuthedRequest } from "../guards/auth.guards";

export const CurrentUser = createParamDecorator(
  (_data: unknown, ctx: ExecutionContext): SessionUser => {
    const req = ctx.switchToHttp().getRequest<AuthedRequest>();
    if (!req.user) {
      throw new Error("CurrentUser used without AuthGuard");
    }
    return req.user;
  },
);
