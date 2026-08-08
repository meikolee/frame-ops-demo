# FRAME API — PM2 process file
# Usage: pm2 start deploy/ecosystem.config.cjs

module.exports = {
  apps: [
    {
      name: "frame-api",
      cwd: "./apps/api",
      script: "dist/main.js",
      instances: 1,
      exec_mode: "fork",
      env: {
        NODE_ENV: "production",
        PORT: 8787,
      },
      error_file: "./logs/api-error.log",
      out_file: "./logs/api-out.log",
      merge_logs: true,
      max_memory_restart: "400M",
    },
    {
      name: "frame-web",
      cwd: "./apps/web",
      script: "node_modules/next/dist/bin/next",
      args: "start -p 3088",
      instances: 1,
      env: {
        NODE_ENV: "production",
        NEXT_PUBLIC_API_BASE: "https://frame.example.com/api",
        NEXT_PUBLIC_SITE_URL: "https://frame.example.com",
      },
      error_file: "./logs/web-error.log",
      out_file: "./logs/web-out.log",
    },
  ],
};
