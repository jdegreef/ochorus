import { describe, expect, it } from 'vitest';
import { sourceHref } from './editionHref';
import type { EntrySource } from './journal';

const src = (kind: EntrySource['kind'], slug: string, order = 1): EntrySource => ({
	kind,
	slug,
	order,
	p: 3,
	edition: 'en',
	title: 't',
	quote: 'q'
});

describe('sourceHref', () => {
	it('links a Notebook entry back to its passage, for every work kind', () => {
		// Each kind has its own route — a new kind must never fall through to
		// another kind's (the bug a ternary chain here invites).
		// (localizeHref settles the trailing slash; the route is what matters.)
		expect(sourceHref(src('book', 'humility', 2))).toMatch(/\/books\/humility\/2\/?\?p=3$/);
		expect(sourceHref(src('sermon', 'himself'))).toMatch(/\/sermons\/himself\/?\?p=3$/);
		expect(sourceHref(src('bio', 'andrew-murray'))).toMatch(/\/authors\/andrew-murray\/?\?p=3$/);
		expect(sourceHref(src('article', 'how-to-pray'))).toMatch(/\/articles\/how-to-pray\/?\?p=3$/);
	});
});
