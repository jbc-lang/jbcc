import { expect, test, type APIRequestContext } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = (path: string) => readFileSync(new URL(`fixtures/includes/${path}`, import.meta.url), "utf8");
const file = (path: string) => ({ path, source: fixture(path) });

function build(request: APIRequestContext, entry: string, files: { path: string; source: string }[], units: string[] = []) {
  return request.post("/api/v1/compile", { data: { entry, units, files } });
}

test("compiles nested and case-sensitive includes with shared files and relative precedence", async ({ request, page }) => {
  const paths = ["app/main.b", "app/I_CHOICE", "I_CHOICE", "I_SHARED", "library/show.b", "library/defs/I_NESTED"];
  const files = paths.map(file);
  await page.addInitScript((files) => {
    localStorage.setItem("jbcc.playground.draft", JSON.stringify({
      files, units: ["library/show.b"], entry: "app/main.b", active: "app/main.b", stdin: "",
    }));
  }, files);
  await page.goto("/");
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Exited with status 0", { timeout: 20000 });
  expect(await page.locator("#stdout").textContent()).toBe("shared-local\nshared\n");

  const wrongCase = files.map((f) => f.path === "I_SHARED" ? { ...f, path: "I_shared" } : f);
  const rejected = await build(request, "app/main.b", wrongCase, ["library/show.b"]);
  expect(rejected.status()).toBe(422);
  expect((await rejected.json()).diagnostics).toEqual([
    { path: "library/defs/I_NESTED", line: 1, column: 1, severity: "error", message: "include file 'I_SHARED' not found" },
  ]);
});

test("diagnoses missing, recursive and out-of-project includes", async ({ request }) => {
  for (const [entry, paths, origin, message] of [
    ["missing.b", ["missing.b"], "missing.b", "include file 'Missing' not found"],
    ["first.b", ["first.b", "second.b"], "second.b", "recursive include 'first.b'"],
    ["app/escape.b", ["app/escape.b"], "app/escape.b", "include escapes project root"],
    ["app/root-fallback.b", ["app/root-fallback.b"], "app/root-fallback.b", "include file '../program.c' not found"],
  ] as const) {
    const response = await build(request, entry, paths.map(file));
    expect(response.status()).toBe(422);
    expect((await response.json()).diagnostics).toEqual([{ path: origin, line: 1, column: 1, severity: "error", message }]);
  }
});

test("rejects unsafe and duplicate names, and enforces request and expanded-source limits", async ({ request }) => {
  const main = file("missing.b");
  for (const files of [
    [main, main],
    [main, { ...main, path: "../outside" }],
    [main, { ...main, path: "missing.b/child" }],
  ]) {
    expect((await build(request, main.path, files)).status()).toBe(400);
  }
  const oversized = await build(request, main.path, [{ ...main, source: "x".repeat(65537) }]);
  expect(oversized.status()).toBe(413);

  const body = await request.post("/api/v1/compile", {
    headers: { "Content-Type": "application/json" },
    data: " ".repeat((512 << 10) + 1),
  });
  expect(body.status()).toBe(413);

  // Generate variants whose depths and sizes exercise the configured limits.
  const chain = Array.from({ length: 18 }, (_, index) => ({
    path: `I${index}`,
    source: index === 17 ? "" : `$INSERT I${index + 1}\n`,
  }));
  const depth = await build(request, "I0", chain);
  expect(depth.status()).toBe(413);
  expect((await depth.json()).diagnostics[0].message).toBe("include depth limit exceeded");

  const expanded = await build(request, "main.b", [
    { path: "main.b", source: "$INSERT BIG\n".repeat(18) },
    { path: "BIG", source: ("* " + "x".repeat(1021) + "\n").repeat(64) },
  ]);
  expect(expanded.status()).toBe(413);
  expect((await expanded.json()).diagnostics[0].message).toBe("expanded source limit exceeded");
});

test("rejects other browser origins and nonlocal host names", async ({ request }) => {
  const response = await request.post("/api/v1/compile", {
    headers: { Origin: "https://example.invalid" },
    data: {},
  });
  expect(response.status()).toBe(403);
  const rebound = await request.get("/", { headers: { Host: "example.invalid" } });
  expect(rebound.status()).toBe(403);
});
