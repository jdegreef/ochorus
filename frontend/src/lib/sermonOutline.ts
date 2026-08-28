/**
 * Build a jump-to-section outline for a sermon.
 *
 * Two structures are recognized, in document order:
 *  - real `<h2>`/`<h3>` headings (some sermons have them), and
 *  - the classic homiletic point structure — a paragraph opening with a Roman
 *    numeral ("I. …", "II. …"), which is how Spurgeon-era sermons mark their
 *    two-to-four main points. The point's thesis is usually an ALL-CAPS run
 *    ("A GOSPEL REJECTED", "PRAYER COMMANDED"); we lift that as the label.
 *
 * Precision over recall: only unambiguous markers become entries, so a sermon
 * with no real structure simply gets no outline rather than a noisy one.
 */
export interface OutlineEntry {
	id: string;
	label: string;
	kind: 'heading' | 'point';
}

const POINT_RE = /^(I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+(.+)/s;
// A run of capitalised words (the point's thesis), ≥2 words so a stray initial
// isn't mistaken for a heading.
// Unicode-aware: an ASCII `[A-Z]` class cuts at the first accented letter, so
// `APLICAÇÃO` came out as "Aplica" and `BENEFÍCIO` as "Benef" in the Spanish
// and Portuguese sermons. `\p{Lu}` is the whole uppercase category.
const CAPS_RUN = /(\p{Lu}[\p{Lu}'’]*(?:[ -]+\p{Lu}[\p{Lu}'’]*){1,})/u;
// A ONE-word thesis, which the run above cannot see: "there is a COMPLAINT",
// "the closing up is to be an EXHORTATION", "Now for the APPLICATION". Five
// letters minimum, which is what keeps an initial or a roman numeral out — and
// across the corpus it matches those three points and nothing else.
const CAPS_WORD = /(\p{Lu}[\p{Lu}'’]{4,})(?![\p{Ll}])/u;
// Failing both, the point's opening SENTENCE can serve if it names the
// division ("The secret of this joy.", "How we may answer some objections.").
//
// The guard that carries the weight is that such a label is NEVER truncated:
// a caps run is the author's own marked thesis, so trimming a long one is
// fair, but a sentence is our inference, and one that does not fit was not a
// title. That rule needs no vocabulary, which is what makes it hold in every
// language — it is what stops `the-ravens-cry` rendering "V. De Novo, Há
// Ainda Outro E Muito Mais Poderoso…" in Portuguese while English correctly
// renders nothing.
//
// `CONNECTIVE` is a refinement on top, and English-only by nature: it catches
// the few short openings that would otherwise squeeze through ("But I have
// mightier arguments and nearer the mark."). A sermon in another language
// loses nothing by it — the length rule has already done the work.
const CONNECTIVE = /^(But|Again|Then|Thus|And|So|Yet|Now,|Remember|Well|Moreover|Further)\b/;
//: A title-shaped head may close with a colon or a dash as readily as a stop —
//: `the-possibilities-of-faith` opens its first point "Let us consider the
//: possibilities of faith:--".
const SENTENCE_END = /^[^.!?:]*[.!?:]/;
//: How many words a drawer entry may run to.
const MAX_LABEL_WORDS = 9;

function titleCase(s: string): string {
	return (
		s
			.toLowerCase()
			// Only after a space or a dash — NOT after an apostrophe, which `\b`
			// treats as a boundary and which turned "GOD'S" into "God'S".
			// `\p{Ll}` rather than `[a-z]`, or an accented opening is left in
			// lower case: "é Necessário Que A Nossa Causa…".
			.replace(/(^|[\s—–-])(\p{Ll})/gu, (_, before, c) => before + c.toUpperCase())
			.trim()
	);
}

/** A homiletic point label from a paragraph's leading text, or null. */
export function pointLabel(text: string): string | null {
	const m = text.trim().replace(/\s+/g, ' ').match(POINT_RE);
	if (!m) return null;
	const rest = m[2];
	const caps = rest.match(CAPS_RUN) ?? rest.match(CAPS_WORD);
	let label: string;
	if (caps) {
		label = caps[1];
	} else {
		// No thesis in caps. Take the opening sentence only if it reads as a
		// title; otherwise this point gets no entry, which is what the module's
		// precision-over-recall promise requires. The old fallback took the
		// leading words unconditionally and truncated them, which put eleven
		// half-sentences into the drawers of eight sermons.
		const first = (rest.match(SENTENCE_END) ?? [''])[0].trim();
		if (!first || CONNECTIVE.test(first)) return null;
		label = titleCase(first).replace(/[.,;:—–-]+$/, '').trim();
		// Never truncated — see above. This is also why the cap below can only
		// ever apply to a caps run.
		if (label.split(' ').length > MAX_LABEL_WORDS) return null;
		return `${m[1]}. ${label}`;
	}
	label = titleCase(label).replace(/[.,;:—–-]+$/, '').trim();
	const words = label.split(' ');
	if (words.length > MAX_LABEL_WORDS) label = words.slice(0, MAX_LABEL_WORDS).join(' ') + '…';
	return label ? `${m[1]}. ${label}` : null;
}

/**
 * Scan a rendered sermon body, assign stable ids to section anchors, and return
 * the outline. Mutates the DOM (adds ids) — call after the body is in the page.
 */
export function buildOutline(container: HTMLElement): OutlineEntry[] {
	const entries: OutlineEntry[] = [];
	let n = 0;
	for (const el of Array.from(container.children) as HTMLElement[]) {
		const tag = el.tagName;
		// H2 through H6. It was H2/H3, and two sermons set their side-heads as
		// `<h4>` — `come-thou-into-the-ark` ("A Solemn Message.", "Judgment.")
		// and `rest` — so both had real, good headings and no outline at all.
		if (/^H[2-6]$/.test(tag)) {
			const label = (el.textContent || '').trim().replace(/\s+/g, ' ');
			if (!label) continue;
			el.id = el.id || `sec-${n++}`;
			entries.push({ id: el.id, label, kind: 'heading' });
		} else if (tag === 'P') {
			const label = pointLabel(el.textContent || '');
			if (!label) continue;
			el.id = el.id || `sec-${n++}`;
			entries.push({ id: el.id, label, kind: 'point' });
		}
	}
	return entries;
}
