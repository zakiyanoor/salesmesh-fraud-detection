import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "./server";

const SRC = join(import.meta.dirname, "..");

function sourceFiles(dir = SRC) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === "test" ? [] : sourceFiles(path);
    return /\.(js|jsx)$/.test(name) && !/\.test\.(js|jsx)$/.test(name) ? [path] : [];
  });
}

const files = sourceFiles().map((path) => ({ name: relative(SRC, path).replaceAll("\\", "/"), text: readFileSync(path, "utf-8") }));
const using = (pattern) => files.filter((f) => pattern.test(f.text)).map((f) => f.name);

describe("client security (source scan)", () => {
  it("never injects HTML or evaluates code", () => {
    expect(using(/dangerouslySetInnerHTML|\.innerHTML|\beval\(|new Function\(/)).toEqual([]);
  });

  it("no app code touches browser storage (MUI keeps the theme choice), and no code reads cookies", () => {
    expect(using(/localStorage|sessionStorage|indexedDB/)).toEqual([]);
    expect(using(/document\.cookie/)).toEqual([]);
  });

  it("only the API helper calls fetch, and only it sends credentials, to the configured base", () => {
    expect(using(/\bfetch\(/)).toEqual(["api.js"]);
    expect(using(/credentials/)).toEqual(["api.js"]);
    const api = files.find((f) => f.name === "api.js").text;
    expect(api).toMatch(/fetch\(`\$\{API_BASE\}\$\{path\}/);
    expect(api).toMatch(/const API_BASE = \(import\.meta\.env\.VITE_API_BASE \|\| "\/api"\)/);
  });
});

describe("session end", () => {
  it("a 401 goes to the sign-in page once, without a request loop", async () => {
    const { calls } = mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/review-decisions": reply(401, { error: "Authentication required" }) });
    renderApp("/history");
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
    const settled = calls.length;
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(calls.length).toBe(settled);
    expect(calls.filter((c) => c.path === "/api/me")).toHaveLength(1);
  });

  it("logout clears the signed-in state, so Back cannot show a page again", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/history");
    await screen.findByRole("heading", { name: "Review history", level: 1 });
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Review history" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  });
});
