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

function titleCase(s: string): string {
	return s
		.toLowerCase()
		.replace(/\b([a-z])/g, (_, c) => c.toUpperCase())
		.trim();
}

/** A homiletic point label from a paragraph's leading text, or null. */
export function pointLabel(text: string): string | null {
	const m = text.trim().replace(/\s+/g, ' ').match(POINT_RE);
	if (!m) return null;
	const rest = m[2];
	const caps = rest.match(CAPS_RUN);
	let label = caps ? caps[1] : rest;
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
		if (tag === 'H2' || tag === 'H3') {
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
