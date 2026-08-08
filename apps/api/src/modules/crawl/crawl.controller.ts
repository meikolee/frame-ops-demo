import { Body, Controller, Get, Inject, Post, UseGuards } from "@nestjs/common";
import { IsUrl } from "class-validator";
import { ApiResult, CrawlJob, ok } from "@frame/shared";
import { CrawlService } from "./crawl.service";
import {
  AuthGuard,
  PermissionsGuard,
  RequirePermissions,
} from "../../common/guards/auth.guards";

class CrawlDto {
  @IsUrl({ require_protocol: true })
  url!: string;
}

@Controller("crawl")
@UseGuards(AuthGuard, PermissionsGuard)
export class CrawlController {
  constructor(@Inject(CrawlService) private readonly crawl: CrawlService) {}

  @Post()
  @RequirePermissions("crawl:run")
  enqueue(@Body() body: CrawlDto): ApiResult<CrawlJob> {
    return ok(this.crawl.enqueue(body.url));
  }

  @Get("jobs")
  @RequirePermissions("crawl:run")
  jobs(): ApiResult<CrawlJob[]> {
    return ok(this.crawl.list());
  }
}
