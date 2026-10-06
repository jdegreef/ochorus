import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReaderText, type ReaderTextOptions } from './readerText.svelte';
import { marks } from './marks.svelte';
import { DEFAULT_HIGHLIGHT } from './reading-schema';
import { listen } from './listen.svelte';

// The note editor and the selection-bar handlers, which the chapter, sermon and
// biography readers now all run. `attach()` is deliberately not called: these
// pin the decisions, not the effects — those need a component to live in and are
// exercised in the browser instead.
const build = (over: Partial<ReaderTextOptions> = {}) =>
	new ReaderText({
		kind: () => 'book',
		slug: () => 'godliness',
		order: () => 1,
		language: () => 'en',
		body: () => undefined,
		topIndex: () => 0,
		listenTitle: () => 'Chapter One',
		listenArtist: () => 'Andrew Murray · Godliness',
		cite: () => ({ author: 'Andrew Murray', book: 'Godliness', chapter: 'One', url: '/x' }),
		...over
	});

const SEG = [{ p: 0, s: 0, e: 10 }];

beforeEach(() => {
	localStorage.clear();
	marks.load('godliness', 1, 'en', 'book');
});

describe('ReaderText note editor', () => {
	it('opens a fresh note with the selection pending and no mark yet', () => {
		const r = build();
		r.openNoteForSelection(SEG);
		expect(r.open).toBe(true);
		expect(r.id).toBe(null);
		expect(r.pending).toEqual(SEG);
		expect(r.draft).toBe('');
		expect(r.color).toBe(DEFAULT_HIGHLIGHT);
		// Nothing is written until the note is saved — opening the editor and
		// closing it must not leave a stray highlight behind.
		expect(marks.list).toHaveLength(0);
	});

	it('saves a fresh note as a new mark', () => {
		const r = build();
		r.openNoteForSelection(SEG);
		r.draft = 'a thought';
		r.saveNote();
		expect(r.open).toBe(false);
		expect(marks.list).toHaveLength(1);
		expect(marks.getNote(marks.list[0].id)).toBe('a thought');
	});

	// Save is not Cancel: a fresh selection saved with no words keeps the
	// highlight, in the colour picked. (It used to save nothing at all — the
	// colour chosen, and the highlight, were silently dropped.)
	it('keeps the highlight when a fresh note is saved empty', () => {
		const r = build();
		r.openNoteForSelection(SEG);
		r.draft = '   ';
		r.color = 'blue';
		r.saveNote();
		expect(marks.list).toHaveLength(1);
		expect(marks.getNote(marks.list[0].id)).toBe('');
		expect(marks.getColor(marks.list[0].id)).toBe('blue');
	});

	it('edits the existing mark when the selection is already highlighted', () => {
		const r = build();
		const id = marks.add(SEG, 'first', DEFAULT_HIGHLIGHT);
		r.openNoteForSelection(SEG);
		expect(r.id).toBe(id);
		expect(r.pending).toEqual([]);
		expect(r.draft).toBe('first');
		r.draft = 'second';
		r.saveNote();
		expect(marks.list).toHaveLength(1);
		expect(marks.getNote(id)).toBe('second');
	});

	// Clearing the text of an EXISTING mark keeps the highlight — only the note
	// goes. The empty-draft rule above applies to fresh selections alone.
	it('keeps an existing mark when its note is cleared', () => {
		const r = build();
		const id = marks.add(SEG, 'first', DEFAULT_HIGHLIGHT);
		r.openNoteForSelection(SEG);
		r.draft = '';
		r.saveNote();
		expect(marks.list).toHaveLength(1);
		expect(marks.getNote(id)).toBe('');
	});

	it('removes the mark outright on remove', () => {
		const r = build();
		marks.add(SEG, 'first', DEFAULT_HIGHLIGHT);
		r.openNoteForSelection(SEG);
		r.removeMark();
		expect(r.open).toBe(false);
		expect(marks.list).toHaveLength(0);
	});

	it('closes without writing anything', () => {
		const r = build();
		r.openNoteForSelection(SEG);
		r.draft = 'typed but abandoned';
		r.close();
		expect(r.open).toBe(false);
		expect(marks.list).toHaveLength(0);
	});
});

describe('ReaderText selection bar', () => {
	it('highlights, recolours, then un-highlights on the same colour', () => {
		const r = build();
		r.onHighlight(SEG, 'blue');
		expect(marks.list).toHaveLength(1);
		expect(r.highlightColor(SEG)).toBe('blue');

		r.onHighlight(SEG, 'green');
		expect(marks.list, 'a different colour recolours rather than adding').toHaveLength(1);
		expect(r.highlightColor(SEG)).toBe('green');

		r.onHighlight(SEG, 'green');
		expect(marks.list, 'the same colour again is a toggle off').toHaveLength(0);
		expect(r.highlightColor(SEG)).toBe(null);
	});
});

describe('ReaderText scripture taps', () => {
	// The chapter reader's own click handler asks this first: a tap it handled
	// must not also be read as an edge-zone page turn.
	const clickOn = (html: string, init: MouseEventInit = {}) => {
		document.body.innerHTML = html;
		const target = document.body.querySelector('span') ?? document.body;
		const e = new MouseEvent('click', { bubbles: true, cancelable: true, ...init });
		Object.defineProperty(e, 'target', { value: target });
		return { handled: new ReaderText({} as ReaderTextOptions).onScriptureClick(e), e };
	};

	it('reports a reference tap as handled and suppresses the default', () => {
		const { handled, e } = clickOn(
			'<a class="scripture-ref" data-ref="John 3:16"><span>John 3:16</span></a>'
		);
		expect(handled).toBe(true);
		expect(e.defaultPrevented).toBe(true);
	});

	it('leaves an ordinary tap alone', () => {
		const { handled, e } = clickOn('<p><span>just some prose</span></p>');
		expect(handled).toBe(false);
		expect(e.defaultPrevented).toBe(false);
	});

	// A reference with no ref to show is not a reference — passing it through is
	// what lets the page turn instead of swallowing the tap.
	it('leaves a scripture-ref carrying no ref alone', () => {
		const { handled } = clickOn('<a class="scripture-ref"><span>Somewhere</span></a>');
		expect(handled).toBe(false);
	});

	// Cmd/Ctrl-click on a linked reference opens its scripture page in a new tab.
	it('lets a modified click on a linked reference through to the browser', () => {
		const linked =
			'<a class="scripture-ref" href="/scripture/john/17/" data-ref="John 17"><span>John 17</span></a>';
		for (const init of [{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { button: 1 }]) {
			const { handled, e } = clickOn(linked, init);
			expect(handled).toBe(false);
			expect(e.defaultPrevented).toBe(false);
		}
		expect(clickOn(linked).handled, 'a plain tap still opens the popover').toBe(true);
	});
});

describe('ReaderText read-aloud', () => {
	const bodyOf = (...texts: string[]) => {
		const el = document.createElement('div');
		el.innerHTML = texts.map((t) => `<p>${t}</p>`).join('');
		return el;
	};

	it('speaks the questions after the text, and stops there instead of rolling on', () => {
		const start = vi.spyOn(listen, 'start').mockImplementation(() => {});
		const onListenFinish = vi.fn();
		const body = bodyOf('Once upon a time.', 'The end.');
		build({
			body: () => body,
			onListenFinish,
			listenEpilogue: () => ['Talk about it together', 'Why did he run?'],
			listenGentle: () => true
		}).startListening(0);
		const [paragraphs, , opts] = start.mock.calls[0];
		expect(paragraphs).toEqual(['Once upon a time.', 'The end.', 'Talk about it together', 'Why did he run?']);
		expect(opts?.onFinish).toBeUndefined();
		expect(opts?.gentle).toBe(true);
		start.mockRestore();
	});

	it('rolls on to the next chapter when there is nothing to ask', () => {
		const start = vi.spyOn(listen, 'start').mockImplementation(() => {});
		const onListenFinish = vi.fn();
		build({ body: () => bodyOf('Text.'), onListenFinish }).startListening(0);
		expect(start.mock.calls[0][2]?.onFinish).toBe(onListenFinish);
		expect(start.mock.calls[0][2]?.gentle).toBe(false);
		start.mockRestore();
	});
});
