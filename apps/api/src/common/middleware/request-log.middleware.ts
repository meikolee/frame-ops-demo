import { Injectable, NestMiddleware } from "@nestjs/common";
import { NextFunction, Request, Response } from "express";

/** Request logging middleware — mirrors the Nest middleware pipeline story. */
@Injectable()
export class RequestLogMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    const started = Date.now();
    res.on("finish", () => {
      const ms = Date.now() - started;
      // eslint-disable-next-line no-console
      console.log(
        `[${new Date().toISOString()}] ${req.method} ${req.originalUrl} -> ${res.statusCode} ${ms}ms`,
      );
    });
    next();
  }
}
