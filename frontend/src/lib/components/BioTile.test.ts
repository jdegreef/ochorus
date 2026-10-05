import { mount, unmount } from "svelte";
import { afterEach, describe, expect, it } from "vitest";

import BioTile from "./BioTile.svelte";
import type { AuthorBio } from "$lib/library-public";

/**
 * The grid tile counts everything a writer has here. It used to print books
 * OR sermons — Wesley read "2 books" with his sermons unmentioned — so a
 * writer with both now shows both.
 */
const author = (book_count: number, sermon_count: number): AuthorBio =>
  ({
    slug: "john-wesley",
    name: "John Wesley",
    photo_url: null,
    book_count,
    sermon_count,
  }) as unknown as AuthorBio;

let target: HTMLElement;
let component: Record<string, unknown> | undefined;

const counts = (a: AuthorBio): string => {
  teardown();
  target = document.createElement("div");
  document.body.appendChild(target);
  component = mount(BioTile, { target, props: { author: a } }) as Record<
    string,
    unknown
  >;
  return (target.querySelector(".text-micro")?.textContent ?? "")
    .replace(/\s+/g, " ")
    .trim();
};

const teardown = () => {
  if (component) unmount(component);
  target?.remove();
  component = undefined;
};

afterEach(teardown);

describe("BioTile counts", () => {
  it("shows books and sermons when a writer has both", () => {
    expect(counts(author(2, 11))).toBe("2 books · 11 sermons");
  });

  it("shows only the count a writer has", () => {
    expect(counts(author(1, 0))).toBe("1 book");
    expect(counts(author(0, 1))).toBe("1 sermon");
  });

  it("shows nothing for a writer with neither", () => {
    expect(counts(author(0, 0))).toBe("");
  });
});
