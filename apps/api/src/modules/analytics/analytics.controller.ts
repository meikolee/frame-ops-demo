import { Body, Controller, Get, Inject, Post, Query, UseGuards } from "@nestjs/common";
import {
  IsIn,
  IsObject,
  IsOptional,
  IsString,
  MinLength,
} from "class-validator";
import {
  AnalyticsEventInput,
  AnalyticsEventName,
  AnalyticsSummary,
  ApiResult,
  ok,
} from "@frame/shared";
import { AnalyticsService } from "./analytics.service";
import {
  AuthGuard,
  PermissionsGuard,
  RequirePermissions,
} from "../../common/guards/auth.guards";

class TrackDto implements AnalyticsEventInput {
  @IsIn(["page_view", "video_play", "video_complete", "cta_click"])
  name!: AnalyticsEventName;

  @IsString()
  @MinLength(1)
  path!: string;

  @IsString()
  visitorId!: string;

  @IsString()
  sessionId!: string;

  @IsOptional()
  @IsString()
  videoId?: string;

  @IsOptional()
  @IsObject()
  meta?: Record<string, string | number | boolean>;
}

@Controller("analytics")
export class AnalyticsController {
  constructor(@Inject(AnalyticsService) private readonly analytics: AnalyticsService) {}

  @Post("track")
  track(@Body() body: TrackDto): ApiResult<{ id: number }> {
    return ok(this.analytics.track(body));
  }

  @Get("summary")
  @UseGuards(AuthGuard, PermissionsGuard)
  @RequirePermissions("analytics:read")
  summary(@Query("days") days = "7"): ApiResult<AnalyticsSummary> {
    return ok(this.analytics.summary(Number(days) || 7));
  }
}
