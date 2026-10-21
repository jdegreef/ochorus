/**
 * Validate the reader's routing rules in `render.yaml`.
 *
 * Those rules are the only thing standing between an inbound link and a
 * usable page, and every failure mode they have is silent. A typo'd `source`
 * simply never matches. A `destination` that isn't a real page 301s a visitor
 * into the not-found shell. A rule pointing at its own source loops forever.
 * None of that shows up in a diff, a build, or a smoke test of the homepage —
 * only in a crawler's report, weeks later.
 *
 * So the rules get checked like code. This deliberately parses the file with a
 * narrow line scanner rather than pulling in a YAML dependency: the block is
 * uniform `- type: / source: / destination:` triples, and the first assertion
 * below fails loudly if that ever stops being true, instead of silently
 * matching nothing and passing.
 */
import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { SHELL_ROUTES } from "./shellRoutes";

const REPO = join(process.cwd(), "..");

interface Rule {
  type: string;
  source: string;
  destination: string;
  line: number;
}

function rules(): Rule[] {
  const lines = readFileSync(join(REPO, "render.yaml"), "utf-8").split("\n");
  const out: Rule[] = [];
  for (let i = 0; i < lines.length; i++) {
    const type = /^\s*-\s*type:\s*(\S+)\s*$/.exec(lines[i]);
    if (!type) continue;
    const source = /^\s*source:\s*(\S+)\s*$/.exec(lines[i + 1] ?? "");
    const destination = /^\s*destination:\s*(\S+)\s*$/.exec(lines[i + 2] ?? "");
    if (!source || !destination) continue;
    out.push({
      type: type[1],
      source: source[1],
      destination: destination[1],
      line: i + 1,
    });
  }
  return out;
}

describe("render.yaml routing rules", () => {
  const all = rules();

  it("parses as a recognisable set of rules", () => {
    // Guards the guard: if the file's shape changes, every assertion below
    // would pass vacuously against an empty list.
    expect(all.length).toBeGreaterThan(40);
    expect(all.some((r) => r.type === "redirect")).toBe(true);
    expect(all.some((r) => r.destination === "/200.html")).toBe(true);
  });

  it("has no rule that redirects a path to itself", () => {
    // Render's matcher is trailing-slash-insensitive, so `/x` -> `/x/` is a
    // loop too, not just an exact self-reference. This is the failure the
    // no-slash-to-slash rules were left out to avoid; it must not creep back.
    const strip = (p: string) => (p.length > 1 ? p.replace(/\/$/, "") : p);
    const loops = all.filter(
      (r) => r.type === "redirect" && strip(r.source) === strip(r.destination),
    );
    expect(
      loops.map((r) => `${r.source} -> ${r.destination} (line ${r.line})`),
    ).toEqual([]);
  });

  it("never redirects to a path that is itself redirected", () => {
    // A chained 301 leaks link equity and costs a round trip; Render will not
    // collapse it for us.
    const sources = new Map(
      all.filter((r) => r.type === "redirect").map((r) => [r.source, r]),
    );
    const chained = all
      .filter((r) => r.type === "redirect" && sources.has(r.destination))
      .map((r) => `${r.source} -> ${r.destination} -> …(line ${r.line})`);
    expect(chained).toEqual([]);
  });

  it("declares each source once", () => {
    // Two rules for one path: the second is dead, and which one that is
    // depends on ordering nobody is thinking about.
    const seen = new Map<string, number>();
    const dupes: string[] = [];
    for (const r of all) {
      if (seen.has(r.source))
        dupes.push(`${r.source} (lines ${seen.get(r.source)}, ${r.line})`);
      else seen.set(r.source, r.line);
    }
    expect(dupes).toEqual([]);
  });

  it("redirects only to pages that exist", () => {
    // A 301 to a page that is not built lands the visitor on the not-found
    // page with an extra hop. Every kept redirect names a real index page or a
    // prerendered detail page we can see in the route tree.
    const ROUTES = join(process.cwd(), "src", "routes");
    const broken = all
      .filter((r) => r.type === "redirect" && r.destination.startsWith("/"))
      .filter((r) => {
        const first = r.destination.split("/").filter(Boolean)[0];
        return first !== undefined && !existsSync(join(ROUTES, first));
      })
      .map((r) => `${r.source} -> ${r.destination} (line ${r.line})`);
    expect(broken).toEqual([]);
  });

  it("stays well under the route count Render will apply", () => {
    // Render caps a static site at 200 redirect/rewrite rules, and a rule
    // removed from this file is NOT removed from the service — the sync only
    // adds and updates. Leftovers took ochorus-web to the cap in 2026-10 and
    // every Blueprint sync failed silently from then on (the /vi and /ko pages
    // never got their rules). Keep this small: add a locale or a page with a
    // `:lang` rule, never a copy per locale, and retire old-site redirects once
    // Search Console shows no traffic to them. Removing a rule here also means
    // deleting it in the dashboard (ochorus-web → Redirects/Rewrites).
    expect(all.length).toBeLessThanOrEqual(70);
  });

  it("has no catch-all, so a missing page answers 404", () => {
    // A wildcard or placeholder rewrite turns every miss under it into a 200 —
    // the soft-404 pile this file used to create (`/* -> /200.html`). Misses
    // belong to Render's /404.html (scripts/build-404.mjs). The only rules onto
    // the 200 shell are the client-only app routes ($lib/shellRoutes), bare and
    // under `/:lang`; the only other pattern is `/:lang/<page>` onto that
    // locale's own index file. Anything else here is a leak.
    const shell = new Set(SHELL_ROUTES.flatMap((r) => [r, `/:lang${r}`]));
    const localeIndex = (r: Rule) =>
      /^\/:lang\/[a-z-]+$/.test(r.source) &&
      r.destination === `${r.source}.html`;
    const leaks = all.filter(
      (r) =>
        r.type === "rewrite" &&
        (/[*:]/.test(r.source) || r.destination === "/200.html") &&
        !shell.has(r.source) &&
        !localeIndex(r),
    );
    expect(
      leaks.map((r) => `${r.source} -> ${r.destination} (line ${r.line})`),
    ).toEqual([]);
  });
});

describe("render.yaml cache headers", () => {
  /** Every `- path: … / name: Cache-Control / value: "…"` triple, by path. */
  function cacheRules(): Map<string, string> {
    const lines = readFileSync(join(REPO, "render.yaml"), "utf-8").split("\n");
    const out = new Map<string, string>();
    for (let i = 0; i < lines.length; i++) {
      const path = /^\s*-\s*path:\s*(\S+)\s*$/.exec(lines[i]);
      if (!path || !/^\s*name:\s*Cache-Control\s*$/.test(lines[i + 1] ?? ""))
        continue;
      const value = /^\s*value:\s*"(.+)"\s*$/.exec(lines[i + 2] ?? "");
      if (value) out.set(path[1], value[1]);
    }
    return out;
  }

  it("pins only content-hashed names", () => {
    // Header rules match the PATH, never the query string, and a browser told
    // `immutable` (or a months-long max-age) keeps the file with no way to
    // purge it. Only Vite's /_app/immutable/ renames a file when its bytes
    // change; /covers, /portraits and the rest keep their names across a
    // redraw, so pinning them freezes the old art for everyone who saw it.
    // render.yaml's cache comment says why `?v=` URLs were not enough.
    const rules = cacheRules();
    expect(rules.get("/_app/immutable/*")).toContain("immutable");
    expect(rules.has("/covers/*")).toBe(true);
    const pinned = [...rules].filter(
      ([, v]) =>
        v.includes("immutable") ||
        Number(/max-age=(\d+)/.exec(v)?.[1] ?? 0) > 604800,
    );
    expect(pinned.map(([p]) => p)).toEqual(["/_app/immutable/*"]);
  });
});
