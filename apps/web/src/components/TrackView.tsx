"use client";

import { useEffect } from "react";
import { trackPageView } from "@/lib/api";

/** Client Component: fires PV after hydration — keeps Server Component page pure. */
export function TrackView({ path, videoId }: { path: string; videoId?: string }) {
  useEffect(() => {
    void trackPageView(path, videoId).catch(() => undefined);
  }, [path, videoId]);
  return null;
}
