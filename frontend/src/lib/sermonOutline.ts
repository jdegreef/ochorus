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
const CAPS_RUN = /\b([A-Z][A-Z'’]*(?:[ -]+[A-Z][A-Z'’]*){1,})/;
// A ONE-word thesis, which the run above cannot see: "there is a COMPLAINT",
// "the closing up is to be an EXHORTATION", "Now for the APPLICATION". Five
// letters minimum, which is what keeps an initial or a roman numeral out — and
// across the corpus it matches those three points and nothing else.
const CAPS_WORD = /\b([A-Z][A-Z'’]{4,})\b/;
// Failing both, the point's opening SENTENCE can serve if it names the
// division ("The secret of this joy.", "How we may answer some objections.").
// Two conditions keep that from becoming noise, and both were measured:
// a title is short, and it does not open with a connective — those are the
// preacher carrying his argument forward, and truncating one gives
// "I. I Argue That He Will, First, When…", which is worse than no entry.
const MAX_SENTENCE_WORDS = 10;
const CONNECTIVE = /^(But|Again|Then|Thus|And|So|Yet|Now,|Remember|Well|Moreover|Further)\b/;

function titleCase(s: string): string {
	return (
		s
			.toLowerCase()
			// Only after a space or a dash — NOT after an apostrophe, which `\b`
			// treats as a boundary and which turned "GOD'S" into "God'S".
			.replace(/(^|[\s—–-])([a-z])/g, (_, before, c) => before + c.toUpperCase())
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
		const first = (rest.match(/^[^.!?]*[.!?]/) ?? [''])[0].trim();
		if (!first || first.split(' ').length > MAX_SENTENCE_WORDS || CONNECTIVE.test(first)) {
			return null;
		}
		label = first;
	}
	label = titleCase(label).replace(/[.,;:—–-]+$/, '').trim();
	const words = label.split(' ');
	if (words.length > 9) label = words.slice(0, 9).join(' ') + '…';
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
