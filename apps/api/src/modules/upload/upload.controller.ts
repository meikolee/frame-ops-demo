import {
  Body,
  Controller,
  Inject,
  Param,
  Post,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from "@nestjs/common";
import { FileInterceptor } from "@nestjs/platform-express";
import { IsInt, IsString, Min, MinLength } from "class-validator";
import {
  ApiResult,
  ChunkInitRequest,
  ChunkInitResponse,
  SessionUser,
  fail,
  ok,
} from "@frame/shared";
import { UploadService } from "./upload.service";
import {
  AuthGuard,
  PermissionsGuard,
  RequirePermissions,
} from "../../common/guards/auth.guards";
import { CurrentUser } from "../../common/decorators/current-user.decorator";

class InitDto implements ChunkInitRequest {
  @IsString()
  @MinLength(1)
  filename!: string;

  @IsString()
  mimeType!: string;

  @IsInt()
  @Min(1)
  sizeBytes!: number;

  @IsInt()
  @Min(256 * 1024)
  chunkSize!: number;
}

class CompleteDto {
  @IsString()
  uploadId!: string;
}

@Controller("uploads")
@UseGuards(AuthGuard, PermissionsGuard)
export class UploadController {
  constructor(@Inject(UploadService) private readonly uploads: UploadService) {}

  @Post("init")
  @RequirePermissions("upload:write")
  init(
    @Body() body: InitDto,
    @CurrentUser() user: SessionUser,
  ): ApiResult<ChunkInitResponse> {
    return ok(this.uploads.init(body, user.id));
  }

  @Post(":uploadId/chunks/:index")
  @RequirePermissions("upload:write")
  @UseInterceptors(FileInterceptor("chunk"))
  chunk(
    @Param("uploadId") uploadId: string,
    @Param("index") index: string,
    @UploadedFile() file?: Express.Multer.File,
  ): ApiResult<{ received: number; total: number }> {
    if (!file) return fail("NO_CHUNK", "Missing multipart field `chunk`");
    const result = this.uploads.receiveChunk(uploadId, Number(index), file.buffer);
    if (!result) return fail("NOT_FOUND", "Upload session not found");
    return ok(result);
  }

  @Post("complete")
  @RequirePermissions("upload:write")
  complete(@Body() body: CompleteDto): ApiResult<{ key: string; etag: string }> {
    const result = this.uploads.complete(body.uploadId);
    if (!result.ok) return fail(result.code, result.message);
    return ok(result.data);
  }
}
