import { describe, it, expect } from 'vitest';
import { collectionFileName, collectionMarkdown, toMarkdown, type ExportBundle } from './dataExport';
import { cleanEntry, type JournalEntry } from './journal';

const bundle: ExportBundle = {
	app: 'Ochorus',
	exported_at: '2026-07-22T12:00:00.000Z',
	works: [
		{
			kind: 'book',
			slug: 'humility',
			title: 'Humility',
			author: 'Andrew Murray',
			position: { chapter_order: 3, chapter_title: '' },
			highlight_count: 2,
			notes: [{ chapter_order: 3, chapter_title: '', color: 'gold', note: 'convicting' }],
			bookmarks: [{ chapter_title: 'The Humility of Jesus', snippet: 'He humbled himself' }]
		}
	],
	favorites: [{ kind: 'author', slug: 'andrew-murray', title: 'Andrew Murray', saved_at: '2026-01-01T00:00:00.000Z' }],
	journal: [
		{
			kind: 'prayer',
			title: 'For my mother',
			body: 'That she would recover.',
			ref: 'James 5:15',
			written_at: '2026-07-01T09:00:00.000Z',
			answered_at: '2026-07-20T09:00:00.000Z',
			answer: 'She came home today.',
			person: 'Mum',
			updates: [{ at: '2026-07-10T09:00:00.000Z', text: 'Moved out of intensive care.' }],
			source: { title: 'Humility · Chapter 2', quote: 'Humility is the place of entire dependence.' }
		}
	]
};

describe('data export', () => {
	it('renders a readable Markdown digest', () => {
		const md = toMarkdown(bundle);
		expect(md).toContain('# My Ochorus reading');
		expect(md).toContain('Exported 2026-07-22');
		expect(md).toContain('### Humility — Andrew Murray');
		expect(md).toContain('Reading place: chapter 3');
		expect(md).toContain('2 highlights');
		expect(md).toContain('convicting');
		expect(md).toContain('He humbled himself');
		expect(md).toContain('**Andrew Murray**');
		// The Notebook's own writing, with a prayer's answer kept beside it.
		expect(md).toContain('## My Notebook');
		expect(md).toContain('### For my mother — 2026-07-01');
		expect(md).toContain('_Answered prayer for Mum · James 5:15_');
		expect(md).toContain('> — Humility · Chapter 2');
		expect(md).toContain('- 2026-07-10: Moved out of intensive care.');
		expect(md).toContain('**Answered 2026-07-20.** She came home today.');
	});

	it('reports an empty device gracefully', () => {
		const md = toMarkdown({ app: 'Ochorus', exported_at: '2026-07-22T12:00:00.000Z', works: [], favorites: [], journal: [] });
		expect(md).toContain('No reading data on this device yet');
	});
});

describe('collection export', () => {
	const e = (o: Partial<JournalEntry>) => cleanEntry({ id: o.id ?? 'x', kind: 'note', ...o })!;
	it('sets a collection out as Markdown, oldest first', () => {
		const md = collectionMarkdown(
			'Notes on Humility',
			[
				e({ id: 'b', title: 'Dependence', body: 'To let God be all.', createdAt: Date.UTC(2026, 8, 2), ref: 'Phil 2:5',
					source: { kind: 'book', slug: 'humility', order: 1, p: 3, edition: 'en', title: 'Humility · Chapter 1', quote: 'Humility is the place of entire dependence on God.' } }),
				e({ id: 'a', kind: 'prayer', body: 'Make me humble.', person: 'Me', createdAt: Date.UTC(2026, 8, 1),
					answeredAt: Date.UTC(2026, 8, 20), answer: 'Slowly, yes.' })
			],
			'2026-09-23T10:00:00.000Z'
		);
		expect(md.startsWith('# Notes on Humility\n')).toBe(true);
		expect(md.indexOf('## Answered prayer — 2026-09-01')).toBeLessThan(md.indexOf('## Dependence — 2026-09-02'));
		expect(md).toContain('_Note · Phil 2:5_');
		expect(md).toContain('> — Humility · Chapter 1');
		expect(md).toContain('**Answered 2026-09-20.** Slowly, yes.');
	});

	it('names the file after the collection', () => {
		expect(collectionFileName('Notes on Humility')).toBe('notes-on-humility.md');
		expect(collectionFileName('Étude: Romains 8')).toBe('etude-romains-8.md');
		expect(collectionFileName('***')).toBe('collection.md');
	});
});

