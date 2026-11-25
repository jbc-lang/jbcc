import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${process.env.JBCC_PLAYGROUND_PORT ?? "18766"}`,
    browserName: (process.env.JBCC_PLAYWRIGHT_BROWSER ?? "chromium") as "chromium" | "firefox" | "webkit",
    channel: process.env.JBCC_PLAYWRIGHT_CHANNEL,
  },
});
