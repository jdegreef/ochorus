import { describe, it, expect } from "vitest";
import {
  foldQuotes,
  quoteStyle,
  smartQuotes,
  smartQuotesHtml,
} from "./smartQuotes";

const en = (s: string) => smartQuotes(s, "en");

describe("smartQuotes (English)", () => {
  it("sets dialogue in curly double quotes", () => {
    expect(en('"But," said he, "do many thirsty persons drink at it?"')).toBe(
      "“But,” said he, “do many thirsty persons drink at it?”",
    );
  });

  it("turns apostrophes in contractions and possessives", () => {
    expect(en("the critic's observation; don't; the saints' rest")).toBe(
      "the critic’s observation; don’t; the saints’ rest",
    );
  });

  it("sets leading elisions and years with an apostrophe, not an opening quote", () => {
    expect(en("'Tis so, 'twas then, give 'em grace, in '45")).toBe(
      "’Tis so, ’twas then, give ’em grace, in ’45",
    );
  });

  it("nests single quotes inside double", () => {
    expect(en("\"He said, 'Come,' and I came.\"")).toBe(
      "“He said, ‘Come,’ and I came.”",
    );
    expect(en("'He cried \"Abba!\" to me.'")).toBe("‘He cried “Abba!” to me.’");
  });

  it("opens after an em dash, a bracket or a slash", () => {
    expect(en('grace—"free grace"—and ("so" it is) and/or "this"')).toBe(
      "grace—“free grace”—and (“so” it is) and/or “this”",
    );
    expect(en("faith—'trust'")).toBe("faith—‘trust’");
  });

  it("closes an interrupted quotation that ends on a dash", () => {
    expect(en('"I thought—" he began')).toBe("“I thought—” he began");
  });

  it("closes a quote set off by a stray space before its punctuation", () => {
    expect(en('the "old paths "? and "one blood ", too')).toBe(
      "the “old paths ”? and “one blood ”, too",
    );
    // …but an opening quote before an ellipsis still opens.
    expect(en('—"...How terrible')).toBe("—“...How terrible");
  });

  it("closes after punctuation", () => {
    expect(en('"Prince of Preachers."')).toBe("“Prince of Preachers.”");
    expect(en('He said "Amen".')).toBe("He said “Amen”.");
  });

  it("leaves text that is already curly exactly as it is", () => {
    const s = "“But,” said he, the critic’s ‘view’ — ’tis «so»";
    expect(en(s)).toBe(s);
  });

  it("leaves a quote stranded between spaces alone", () => {
    expect(en('a " b')).toBe('a " b');
  });

  it("never touches a URL", () => {
    expect(en("see https://example.com/it's\"x\" now 'ok'")).toBe(
      'see https://example.com/it\'s"x" now ‘ok’',
    );
  });

  it("keeps the length, so offsets into it still point at the same words", () => {
    const s = '"But," said he, "the critic\'s \'tis"';
    expect(en(s).length).toBe(s.length);
    expect(foldQuotes(en(s))).toBe(s);
  });
});

describe("quote conventions per language", () => {
  it("knows which languages it may set, by base subtag", () => {
    expect(quoteStyle("en")).toBe("full");
    expect(quoteStyle("en-modern")).toBe("full");
    expect(quoteStyle("pt")).toBe("full");
    expect(quoteStyle("fr")).toBe("apostrophe");
    expect(quoteStyle("uk")).toBe("apostrophe");
    expect(quoteStyle("ar")).toBeNull();
    expect(quoteStyle("am")).toBeNull();
    expect(quoteStyle("de")).toBeNull();
    expect(quoteStyle(undefined)).toBeNull();
  });

  it("French: only the apostrophe inside a word; doubles left for « »", () => {
    expect(smartQuotes(`l'homme dit "oui" et 'non'`, "fr")).toBe(
      `l’homme dit "oui" et 'non'`,
    );
  });

  it("Ukrainian: the apostrophe inside a word", () => {
    expect(smartQuotes(`п'ять "слів"`, "uk")).toBe(`п’ять "слів"`);
  });

  it("leaves an unconfigured language unchanged", () => {
    expect(smartQuotes('"نعم" it\'s', "ar")).toBe('"نعم" it\'s');
  });

  it("does not treat a non-English word as an elision", () => {
    // Swahili quoting a word that happens to read like an English elision.
    expect(smartQuotes("asema, 'em'", "sw")).toBe("asema, ‘em’");
  });

  it("Hindi: a vowel sign before a closing quote counts as part of the word", () => {
    expect(smartQuotes("'हाँ' कहा", "hi")).toBe("‘हाँ’ कहा");
  });
});

describe("smartQuotesHtml", () => {
  const html = (s: string, lang = "en") => smartQuotesHtml(s, lang);

  it("reads quotes across inline tags", () => {
    expect(html('<p>"<em>But</em>," said he.</p>')).toBe(
      "<p>“<em>But</em>,” said he.</p>",
    );
  });

  it("opens a quote at the start of each paragraph, whatever ended the last", () => {
    expect(html('<p>He said:</p><p>"Come."</p>')).toBe(
      "<p>He said:</p><p>“Come.”</p>",
    );
    expect(html("<p>end.</p><blockquote><p>'Tis</p></blockquote>")).toBe(
      "<p>end.</p><blockquote><p>’Tis</p></blockquote>",
    );
  });

  it("leaves tags, attributes and comments alone", () => {
    const s =
      '<p><a class="scripture-ref" data-ref="John 3:16" href=\'/x\'>John 3:16</a><!-- "x" --></p>';
    expect(html(s)).toBe(s);
  });

  it("curls quote entities to the character itself", () => {
    expect(
      html("<p>&quot;Yes,&quot; the critic&#x27;s &#39;view&#39;</p>"),
    ).toBe("<p>“Yes,” the critic’s ‘view’</p>");
  });

  it("treats a no-break space entity as a space", () => {
    expect(html('<p>said&nbsp;"so"</p>')).toBe("<p>said&nbsp;“so”</p>");
  });

  it("skips code and preformatted text", () => {
    const s =
      '<p>run <code>echo "hi" \'x\'</code> then "go"</p><pre>it\'s "raw"</pre>';
    expect(html(s)).toBe(
      '<p>run <code>echo "hi" \'x\'</code> then “go”</p><pre>it\'s "raw"</pre>',
    );
  });

  it("keeps every block's textContent the same length", () => {
    const s =
      "<p>\"But,\" said he, &quot;the <em>critic</em>&#x27;s'</p><p>it's</p>";
    const blocks = (h: string) => {
      const t = document.createElement("template");
      t.innerHTML = h;
      return [...t.content.children].map((el) => el.textContent ?? "");
    };
    const before = blocks(s);
    const after = blocks(html(s));
    expect(after.map((b) => b.length)).toEqual(before.map((b) => b.length));
    expect(after.map(foldQuotes)).toEqual(before);
  });

  it("returns the body untouched for a language it does not set", () => {
    const s = '<p>"x"</p>';
    expect(smartQuotesHtml(s, "ar")).toBe(s);
  });

  it("keeps characters outside the BMP intact", () => {
    expect(html('<p>"𝔊race" it\'s</p>')).toBe("<p>“𝔊race” it’s</p>");
  });
});
