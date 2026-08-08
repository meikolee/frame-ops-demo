import { MiddlewareConsumer, Module, NestModule } from "@nestjs/common";
import { DatabaseModule } from "./db/database.module";
import { RequestLogMiddleware } from "./common/middleware/request-log.middleware";
import { AuthGuard, PermissionsGuard } from "./common/guards/auth.guards";
import { AuthModule } from "./modules/auth/auth.module";
import { VideosModule } from "./modules/videos/videos.module";
import { AnalyticsModule } from "./modules/analytics/analytics.module";
import { UploadModule } from "./modules/upload/upload.module";
import { CrawlModule } from "./modules/crawl/crawl.module";
import { RbacModule } from "./modules/rbac/rbac.module";
import { HealthController } from "./health.controller";

@Module({
  imports: [
    DatabaseModule,
    AuthModule,
    VideosModule,
    AnalyticsModule,
    UploadModule,
    CrawlModule,
    RbacModule,
  ],
  controllers: [HealthController],
  providers: [AuthGuard, PermissionsGuard],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(RequestLogMiddleware).forRoutes("{*path}");
  }
}
