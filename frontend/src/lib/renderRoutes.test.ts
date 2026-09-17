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
import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const REPO = join(process.cwd(), '..');
const STATIC = join(process.cwd(), 'static');
const BOOK_FIXTURES = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'books');

interface Rule {
	type: string;
	source: string;
	destination: string;
	line: number;
}

function rules(): Rule[] {
	const lines = readFileSync(join(REPO, 'render.yaml'), 'utf-8').split('\n');
	const out: Rule[] = [];
	for (let i = 0; i < lines.length; i++) {
		const type = /^\s*-\s*type:\s*(\S+)\s*$/.exec(lines[i]);
		if (!type) continue;
		const source = /^\s*source:\s*(\S+)\s*$/.exec(lines[i + 1] ?? '');
		const destination = /^\s*destination:\s*(\S+)\s*$/.exec(lines[i + 2] ?? '');
		if (!source || !destination) continue;
		out.push({ type: type[1], source: source[1], destination: destination[1], line: i + 1 });
	}
	return out;
}

/** A destination we can check exists without running a build. */
function resolves(destination: string): boolean {
	// The catch-all shell and the prerendered index pages are build output, not
	// repo files — they can't be checked here, and the build's own link tests
	// cover them. Anything under static/ is a file we can actually look for.
	if (destination.endsWith('.html')) return true;
	if (destination.startsWith('/books/') || destination.startsWith('/biographies')) return true;
	if (['/books', '/biographies', '/sermons', '/plans', '/topics', '/'].includes(destination))
		return true;
	return existsSync(join(STATIC, destination.replace(/^\//, '')));
}

describe('render.yaml routing rules', () => {
	const all = rules();

	it('parses as a recognisable set of rules', () => {
		// Guards the guard: if the file's shape changes, every assertion below
		// would pass vacuously against an empty list.
		expect(all.length).toBeGreaterThan(60);
		expect(all.some((r) => r.type === 'redirect')).toBe(true);
		expect(all.at(-1)).toMatchObject({ source: '/*', destination: '/200.html' });
	});

	it('has no rule that redirects a path to itself', () => {
		// Render's matcher is trailing-slash-insensitive, so `/x` -> `/x/` is a
		// loop too, not just an exact self-reference. This is the failure the
		// no-slash-to-slash rules were left out to avoid; it must not creep back.
		const strip = (p: string) => (p.length > 1 ? p.replace(/\/$/, '') : p);
		const loops = all.filter((r) => r.type === 'redirect' && strip(r.source) === strip(r.destination));
		expect(loops.map((r) => `${r.source} -> ${r.destination} (line ${r.line})`)).toEqual([]);
	});

	it('never redirects to a path that is itself redirected', () => {
		// A chained 301 leaks link equity and costs a round trip; Render will not
		// collapse it for us.
		const sources = new Map(all.filter((r) => r.type === 'redirect').map((r) => [r.source, r]));
		const chained = all
			.filter((r) => r.type === 'redirect' && sources.has(r.destination))
			.map((r) => `${r.source} -> ${r.destination} -> …(line ${r.line})`);
		expect(chained).toEqual([]);
	});

	it('declares each source once', () => {
		// Two rules for one path: the second is dead, and which one that is
		// depends on ordering nobody is thinking about.
		const seen = new Map<string, number>();
		const dupes: string[] = [];
		for (const r of all) {
			if (seen.has(r.source)) dupes.push(`${r.source} (lines ${seen.get(r.source)}, ${r.line})`);
			else seen.set(r.source, r.line);
		}
		expect(dupes).toEqual([]);
	});

	it('sends every legacy WordPress URL somewhere real', () => {
		const legacy = all.filter((r) => r.source.startsWith('/wp-content/'));
		expect(legacy.length, 'the retired-media rules should be present').toBeGreaterThan(30);
		const broken = legacy
			.filter((r) => !resolves(r.destination))
			.map((r) => `${r.source} -> ${r.destination} (line ${r.line})`);
		expect(broken).toEqual([]);
	});

	it('redirects every retired cover to a file that exists', () => {
		// These point into static/covers/, which IS in the repo — so unlike the
		// page destinations, this is a real existence check, and it is the one
		// that catches a rename.
		const covers = all.filter((r) => r.destination.startsWith('/covers/'));
		expect(covers.length).toBeGreaterThan(0);
		for (const r of covers) {
			expect(
				existsSync(join(STATIC, r.destination.replace(/^\//, ''))),
				`${r.destination} (line ${r.line}) does not exist in static/`
			).toBe(true);
		}
	});

	it('redirects every retired cover to the cover that book wears NOW', () => {
		// Existence is not enough, and twice was not enough either: these rules
		// broke in two consecutive batches when a book swapped its generated plate
		// for a painting, and both times the failure said only "this file is
		// missing", leaving the right destination to be worked out by hand.
		//
		// The fixture already knows the answer — `cover_url` is the cover that
		// book wears — so ask it, and the failure becomes the fix. It also closes
		// a hole the existence check cannot see: if a curated book's plate were
		// ever left behind on disk, the redirect would go on serving a retired
		// design forever and the check above would stay green.
		const covers = all.filter((r) => r.destination.startsWith('/covers/'));
		const byCover = new Map<string, string>();
		for (const file of readdirSync(BOOK_FIXTURES).filter((f) => f.endsWith('.en.json'))) {
			for (const row of JSON.parse(readFileSync(join(BOOK_FIXTURES, file), 'utf-8'))) {
				if (row.model === 'library.book' && row.fields.cover_url) {
					byCover.set(row.fields.slug, row.fields.cover_url);
				}
			}
		}
		const stale = covers
			.map((r) => {
				// `/covers/art/<slug>.jpg` and `/covers/<slug>.svg` both name a slug.
				const slug = r.destination.replace(/^\/covers\/(art\/)?/, '').replace(/\.[a-z0-9]+$/, '');
				const now = byCover.get(slug);
				return now && now !== r.destination
					? `line ${r.line}: -> ${r.destination}, but ${slug} now wears ${now}`
					: null;
			})
			.filter(Boolean);
		expect(
			stale,
			'a retired-cover redirect points at a cover its book no longer wears'
		).toEqual([]);
	});

	it('redirects to book pages that are actually published', () => {
		// The destination has to be a page that will exist in the build, and what
		// decides that is the fixture: an unpublished book is not prerendered, so
		// a 301 to it lands in the not-found shell — strictly worse than the soft
		// 404 the rule replaced. This also catches a slug rename, which would
		// otherwise break one rule out of twenty-seven, silently.
		const BOOKS = join(REPO, 'backend', 'library', 'fixtures', 'content', 'books');
		const targets = all.filter((r) => /^\/books\/[^/]+\/$/.test(r.destination));
		expect(targets.length).toBeGreaterThan(20);
		const broken: string[] = [];
		for (const r of targets) {
			const slug = r.destination.split('/')[2];
			const file = join(BOOKS, `${slug}.en.json`);
			if (!existsSync(file)) {
				broken.push(`${r.destination} (line ${r.line}): no ${slug}.en.json`);
				continue;
			}
			const book = JSON.parse(readFileSync(file, 'utf-8')).find(
				(row: { model: string }) => row.model === 'library.book'
			);
			if (!book?.fields?.is_published) {
				broken.push(`${r.destination} (line ${r.line}): not published`);
			}
		}
		expect(broken).toEqual([]);
	});

	it('keeps the SPA catch-all last', () => {
		// It matches everything. Any rule after it is unreachable.
		const idx = all.findIndex((r) => r.source === '/*');
		expect(idx).toBe(all.length - 1);
	});
});
