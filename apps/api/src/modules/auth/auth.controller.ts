import { Body, Controller, Get, Inject, Post, UseGuards } from "@nestjs/common";
import { IsEmail, IsString, MinLength } from "class-validator";
import { ApiResult, SessionUser, fail, ok } from "@frame/shared";
import { AuthService } from "./auth.service";
import { AuthGuard } from "../../common/guards/auth.guards";
import { CurrentUser } from "../../common/decorators/current-user.decorator";

class LoginDto {
  @IsEmail()
  email!: string;

  @IsString()
  @MinLength(6)
  password!: string;
}

@Controller("auth")
export class AuthController {
  constructor(@Inject(AuthService) private readonly auth: AuthService) {}

  @Post("login")
  login(@Body() body: LoginDto): ApiResult<{ token: string; user: SessionUser }> {
    const user = this.auth.validate(body.email, body.password);
    if (!user) return fail("INVALID_CREDENTIALS", "Email or password incorrect");
    return ok({
      token: `${user.role}:${user.id}`,
      user,
    });
  }

  @Get("me")
  @UseGuards(AuthGuard)
  me(@CurrentUser() user: SessionUser): ApiResult<SessionUser> {
    return ok(user);
  }
}
