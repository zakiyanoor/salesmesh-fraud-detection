import { describe, expect, it } from "vitest";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Issue #20: deploy/Caddyfile allows the inline colour scheme script in index.html by its hash, so the
// deployed app goes blank if the script changes without a new hash.
const read = (relative) => readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8");
const hash = (text) => `'sha256-${createHash("sha256").update(text).digest("base64")}'`;

describe("Content Security Policy", () => {
  const html = read("../../index.html");
  const caddyfile = read("../../../deploy/Caddyfile");
  const policy = /Content-Security-Policy "([^"]+)"/.exec(caddyfile)[1];
  const scripts = [...html.replace(/\r\n/g, "\n").matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);

  it("allows the inline script with LF and with CRLF line endings", () => {
    expect(scripts).toHaveLength(1);
    expect(policy).toContain(hash(scripts[0]));
    expect(policy).toContain(hash(scripts[0].replace(/\n/g, "\r\n")));
  });

  it("allows no other inline script and no other origin", () => {
    expect(policy).toMatch(/script-src 'self' 'sha256-[^;]+;/);
    expect(policy).not.toMatch(/script-src[^;]*unsafe-inline/);
    expect(policy).not.toMatch(/https?:\/\//);
    expect(policy).toContain("frame-ancestors 'none'");
  });
});
