import {
  Body,
  Controller,
  Get,
  Header,
  Inject,
  Param,
  Patch,
  Post,
  Query,
  UseGuards,
} from "@nestjs/common";
import { IsIn, IsString, MinLength } from "class-validator";
import {
  ApiResult,
  Paginated,
  VideoAsset,
  VideoStatus,
  fail,
  ok,
} from "@frame/shared";
import { VideosService } from "./videos.service";
import {
  AuthGuard,
  PermissionsGuard,
  RequirePermissions,
} from "../../common/guards/auth.guards";

class CreateVideoDto {
  @IsString()
  @MinLength(2)
  title!: string;

  @IsString()
  summary!: string;
}

class UpdateStatusDto {
  @IsIn(["draft", "processing", "ready", "published"])
  status!: VideoStatus;
}

@Controller("videos")
export class VideosController {
  constructor(@Inject(VideosService) private readonly videos: VideosService) {}

  @Get()
  list(
    @Query("page") page = "1",
    @Query("pageSize") pageSize = "20",
    @Query("status") status?: string,
  ): ApiResult<Paginated<VideoAsset>> {
    const statusFilter =
      status === "draft" ||
      status === "processing" ||
      status === "ready" ||
      status === "published"
        ? status
        : undefined;
    return ok(
      this.videos.list(Number(page) || 1, Number(pageSize) || 20, statusFilter),
    );
  }

  @Get("public/:slug")
  bySlug(@Param("slug") slug: string): ApiResult<VideoAsset> {
    const video = this.videos.findBySlug(slug);
    if (!video || video.status !== "published") {
      return fail("NOT_FOUND", "Video not found");
    }
    return ok(video);
  }

  @Get(":id/hls/master.m3u8")
  @Header("Content-Type", "application/vnd.apple.mpegurl")
  hlsManifest(@Param("id") id: string): string {
    // Demo HLS master playlist — real pipeline would write this to OSS/CDN.
    return this.videos.buildHlsMaster(id);
  }

  @Post()
  @UseGuards(AuthGuard, PermissionsGuard)
  @RequirePermissions("video:write")
  create(@Body() body: CreateVideoDto): ApiResult<VideoAsset> {
    return ok(this.videos.create(body.title, body.summary));
  }

  @Patch(":id/status")
  @UseGuards(AuthGuard, PermissionsGuard)
  @RequirePermissions("video:publish")
  updateStatus(
    @Param("id") id: string,
    @Body() body: UpdateStatusDto,
  ): ApiResult<VideoAsset> {
    const updated = this.videos.updateStatus(id, body.status);
    if (!updated) return fail("NOT_FOUND", "Video not found");
    return ok(updated);
  }
}
