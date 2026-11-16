import { describe, expect, it } from "vitest";
import { SITE_URL } from "./config";
import { buildLlmsFullTxt, buildLlmsTxt, type LlmsData } from "./llmsTxt";

const data: LlmsData = {
  authors: [
    {
      slug: "andrew-murray",
      name: "Andrew Murray",
      bio: "<p>A South African pastor [and writer].</p>",
      birth_year: 1828,
      death_year: 1917,
      book_count: 30,
      sermon_count: 2,
    },
    {
      slug: "nobody",
      name: "Nobody",
      bio: "",
      birth_year: null,
      death_year: null,
      book_count: 0,
      sermon_count: 0,
    },
  ],
  topics: [
    { slug: "prayer", title: "On Prayer", description: "Books on prayer." },
  ],
  articles: [
    {
      slug: "what-is-the-trinity",
      h1: "What Is the Trinity?",
      description: "One God in three persons.",
    },
  ],
  locales: [["es", "Español"]],
  books: [
    {
      slug: "humility-2",
      title: "Humility",
      subtitle: "The beauty of holiness",
      chapter_count: 12,
      author: { slug: "andrew-murray", name: "Andrew Murray" },
    },
    {
      slug: "john",
      title: "John",
      subtitle: "",
      chapter_count: 21,
      author: { slug: "x", name: "Open Word Bible" },
      series: { slug: "the-bible" },
    },
  ],
  sermons: [
    {
      slug: "the-golden-key-of-prayer",
      title: "The Golden Key of Prayer",
      scripture_ref: "Jeremiah 33:3",
      summary: "God answers.",
      author: { name: "Charles H. Spurgeon" },
    },
  ],
};

describe("buildLlmsTxt", () => {
  const txt = buildLlmsTxt(data);

  it("opens with the llmstxt.org shape: an H1 and a blockquote summary", () => {
    const [h1, blank, quote] = txt.split("\n");
    expect(h1).toBe("# Ochorus");
    expect(blank).toBe("");
    expect(quote.startsWith("> Ochorus is a free online library")).toBe(true);
  });

  it("links every shelf with an absolute slashed URL", () => {
    expect(txt).toContain(`- [Books](${SITE_URL}/books/)`);
    expect(txt).toContain(`- [Español](${SITE_URL}/es/)`);
    expect(txt).toContain(`(${SITE_URL}/llms-full.txt)`);
  });

  it("lists authors with years and a plain one-line bio, and skips empty ones", () => {
    expect(txt).toContain(
      `- [Andrew Murray (1828–1917)](${SITE_URL}/authors/andrew-murray/): A South African pastor and writer.`,
    );
    expect(txt).not.toContain("Nobody");
  });

  it("names topics and articles but not the long book list", () => {
    expect(txt).toContain(`[On Prayer](${SITE_URL}/topics/prayer/)`);
    expect(txt).toContain(
      `[What Is the Trinity?](${SITE_URL}/articles/what-is-the-trinity/)`,
    );
    expect(txt).not.toContain("/books/humility-2/)");
  });
});

describe("buildLlmsFullTxt", () => {
  const txt = buildLlmsFullTxt(data);

  it("adds every book under its author, but not the Bible books", () => {
    expect(txt).toContain("### Andrew Murray");
    expect(txt).toContain(
      `- [Humility](${SITE_URL}/books/humility-2/): The beauty of holiness · 12 chapters`,
    );
    expect(txt).not.toContain("/books/john/");
  });

  it("adds every sermon with its text and summary", () => {
    expect(txt).toContain(
      `- [The Golden Key of Prayer — Charles H. Spurgeon](${SITE_URL}/sermons/the-golden-key-of-prayer/): Jeremiah 33:3 · God answers.`,
    );
  });
});
