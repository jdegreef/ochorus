import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { markVerse } from "./verse";

// Real bodies, copied byte for byte from backend/library/fixtures/content/.
const BUNYAN_STANZA =
  "<p>Then I saw in my dream, that these good companions, when Christian was got down to the bottom of the hill, gave him a loaf of bread, a bottle of wine, and a cluster of raisins; and then he went on his way, </p> <p>“Whilst Christian is among his godly friends, </p> <p>Their golden mouths make him sufficient mends </p> <p>For all his griefs; and when they let him go, </p> <p>He’s clad with northern steel from top to toe.” </p> <p>But now, in this valley of Humiliation, poor Christian was hard put to it; for he had gone but a little way before he espied a foul fiend coming over the field to meet him: his name is Apollyon. </p>";
// pilgrims-progress ch. 15: a lead-in, then a hymn with alternate lines indented.
const MERCY_HYMN =
  " <p>Then said Mercy,</p> <p>“Let the Most Blessed be my guide, </p> <p> If it be his blessed will, </p> <p>Unto his gate, into his fold, </p> <p> Up to his holy hill. </p> <p>And let him never suffer me </p> <p> To swerve, or turn aside </p> <p>From his free-grace and holy ways, </p> <p> Whate’er shall me betide. </p> <p>And let him gather them of mine </p> <p> That I have left behind;</p> <p>Lord, make them pray they may be thine, </p> <p> With all their heart and mind.” </p> <p>Now my old friend p";
// evening-by-evening: a hymn verse with no spaces between blocks, then a heading.
const SPURGEON_HYMN =
  "<p>“Though the night be dark and dreary,</p><p>Darkness cannot hide from thee;</p><p>Thou art he, who, never weary,</p><p>Watchest where thy people be.”</p><h3>April 23</h3>";
// pilgrims-progress ch. 5: dialogue with speaker labels.
const APOLLYON =
  "<p>Apollyon: Whence came you, and whither are you bound? </p> <p>Christian: I am come from the city of Destruction. </p> <p>Apollyon: By this I perceive thou art one of my subjects. </p> <p>Christian: I was, indeed, born in your dominions. </p>";
// at-the-back-of-the-north-wind ch. 9: short lines of quoted dialogue.
const NORTH_WIND =
  "<p>“What do you want to do yourself?”</p><p>“I want to go into the country at your back.”</p><p>“Then you must go through me.”</p><p>“I don’t know what you mean.”</p>";
// letters-of-samuel-rutherford: a letter's close — short, capitalised, no stops.
const RUTHERFORD =
  "<p> Yours, in his sweet Lord Jesus,</p> <p>S. R.</p> <p>Aberdeen, 1637. </p> <hr/>";
// knots-untied ch. 8: a numbered outline.
const KNOTS =
  " <p>I propose in this paper to attempt three things:—</p> <p>I. First, to explain <i>what Regeneration, or being born again, means</i>.</p> <p>II. Secondly, to show <i>the necessity of Regeneration</i>.</p> <p>III. Thirdly, to point out <i>the marks and evidences of Regeneration</i>.</p> <p>If I can mak";

const classes = (html: string) =>
  [...html.matchAll(/<p(?: class="([^"]*)")?>/g)].map((m) => m[1] ?? "");

describe("markVerse", () => {
  it("sets the Pilgrim’s Progress stanza as verse, and only the stanza", () => {
    expect(classes(markVerse(BUNYAN_STANZA))).toEqual([
      "",
      "verse",
      "verse",
      "verse",
      "verse stanza-end",
      "",
    ]);
  });

  it("keeps a lead-in out of the hymn it introduces, and honours alternate indents", () => {
    const c = classes(markVerse(MERCY_HYMN));
    expect(c[0]).toBe(""); // "Then said Mercy,"
    expect(c.slice(1, 13)).toEqual([
      ...Array(5).fill(["verse", "verse indent"]).flat(),
      "verse",
      "verse indent stanza-end",
    ]);
    expect(c[13]).toBe("");
  });

  it("finds a hymn verse with no whitespace between blocks", () => {
    expect(classes(markVerse(SPURGEON_HYMN))).toEqual([
      "verse",
      "verse",
      "verse",
      "verse stanza-end",
    ]);
  });

  it.each([
    ["speaker-labelled dialogue", APOLLYON],
    ["short quoted dialogue", NORTH_WIND],
    ["a letter’s signature", RUTHERFORD],
    ["a numbered outline", KNOTS],
  ])("leaves %s alone", (_, html) => {
    expect(markVerse(html)).toBe(html);
  });

  it("needs three lines, and lines that touch", () => {
    const two =
      "<p>Were the whole realm of nature mine,</p><p>That were a present far too small;</p>";
    expect(markVerse(two)).toBe(two);
    const split =
      "<p>Were the whole realm of nature mine,</p><blockquote><p>That were a present far too small;</p></blockquote><p>Love so amazing, so Divine,</p>";
    expect(markVerse(split)).toBe(split);
  });

  it("changes nothing but the class: same paragraphs, same text", () => {
    const out = markVerse(MERCY_HYMN);
    expect(out.match(/<p\b/g)).toHaveLength(MERCY_HYMN.match(/<p\b/g)!.length);
    expect(out.replace(/<p class="[^"]*">/g, "<p>")).toBe(MERCY_HYMN);
  });

  it("is idempotent", () => {
    const once = markVerse(BUNYAN_STANZA + MERCY_HYMN);
    expect(markVerse(once)).toBe(once);
  });

  it("finds the stanza in the stored chapter, and keeps the dialogue after it prose", () => {
    const file = resolve(
      import.meta.dirname,
      "../../../backend/library/fixtures/content/books/pilgrims-progress.en.json",
    );
    const rows: { fields: { order?: number; body_html?: string } }[] =
      JSON.parse(readFileSync(file, "utf8"));
    const body = rows.find((r) => r.fields.order === 5)!.fields.body_html!;
    const out = markVerse(body);
    expect(out).toMatch(/<p class="verse">“Whilst Christian/);
    expect(out).toMatch(
      /<p class="verse stanza-end">He’s clad with northern steel/,
    );
    expect(out).toMatch(/<p>Apollyon: Whence came you/);
  });
});
