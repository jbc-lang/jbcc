import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";


test("runs another program offline after loading the toolchain", async ({ context, page }) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.includes("/api/")) requests.push(request.url());
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("#filename")).toHaveValue("hello.b");
  await expect(page.getByRole("button", { name: "Sign in with GitHub" })).toBeHidden();
  const run = page.getByRole("button", { name: "Run", exact: true });
  const status = page.locator("#status");
  await run.click();
  await expect(status).toHaveText("Exited with status 0", { timeout: 45_000 });
  await expect(page.locator("#stdout")).toHaveText("Hello, jBC!");

  const factorial = readFileSync(new URL("../../tests/programs/factorial.b", import.meta.url), "utf8");
  await context.setOffline(true);
  await page.getByLabel("jBC source").fill(factorial);
  await run.click();
  await expect(status).toHaveText("Exited with status 0", { timeout: 20_000 });
  await expect(page.locator("#stdout")).toHaveText("2432902008176640000");
  expect(requests).toEqual([]);
});

for (const [statusText, asset, body] of [
  ["Loading Python…", "**/toolchain/**/pyodide.mjs", "await new Promise(() => {});"],
  ["Compiling C…", "**/toolchain/**/bundle.js", "export const commands = { clang: () => new Promise(() => {}) };"],
]) {
  test(`stops during ${statusText} and can start a fresh compiler`, async ({ page }) => {
    await page.route(asset, (route) => route.fulfill({
      contentType: "application/javascript",
      headers: { "Cache-Control": "no-store" },
      body,
    }), { times: 1 });
    await page.goto("/");
    await expect(page.locator("#filename")).toHaveValue("hello.b");
    const run = page.getByRole("button", { name: "Run", exact: true });
    const status = page.locator("#status");
    await run.click();
    await expect(status).toHaveText(statusText);
    await page.getByRole("button", { name: "Stop", exact: true }).click();
    await expect(status).toHaveText("Stopped");
    await run.click();
    await expect(status).toHaveText("Exited with status 0", { timeout: 45_000 });
  });
}

test("a runner opened without an opaque sandbox refuses to execute", async ({ page }) => {
  await page.goto("/");
  const reply = await page.evaluate(async () => {
    const frame = document.createElement("iframe");
    frame.src = "./runner.html";
    const loaded = new Promise<void>((resolve) => frame.addEventListener("load", () => resolve(), { once: true }));
    document.body.append(frame);
    await loaded;
    const channel = new MessageChannel();
    try {
      return await new Promise<unknown>((resolve) => {
        const timer = setTimeout(() => resolve(null), 500);
        channel.port1.onmessage = ({ data }) => {
          clearTimeout(timer);
          resolve(data);
        };
        frame.contentWindow!.postMessage({
          wasm: new Uint8Array(),
          stdin: "",
        }, "*", [channel.port2]);
      });
    } finally {
      channel.port1.close();
      frame.remove();
    }
  });
  expect(reply).toBeNull();
});

test("WASI supplies randomness and browser session values", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#filename")).toHaveValue("hello.b");
  const editor = page.getByLabel("jBC source");
  const run = page.getByRole("button", { name: "Run", exact: true });
  const status = page.locator("#status");
  const stdout = page.locator("#stdout");

  for (const [path, expected] of [
    ["snippets/rnd.b", /^0\n0\nin range\n$/],
    ["programs/unique-key.b", /^(?:[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}\n){5}$/],
    ["programs/pid-uses-native-process-id-with-port-override.b", /^0\n0\n$/],
    ["programs/account-path-uses-working-directory.b", /^\/\n$/],
  ] as const) {
    await editor.fill(readFileSync(new URL(`../../tests/${path}`, import.meta.url), "utf8"));
    await run.click();
    await expect(status).toHaveText("Exited with status 0", { timeout: 20_000 });
    expect(await stdout.textContent()).toMatch(expected);
  }
});
