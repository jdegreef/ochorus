import { flushSync, mount, unmount, type Component } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';
import type { ResumeItem } from '$lib/resumeItems';
import WorkCard from './WorkCard.svelte';
import PlaceholderHost from '../../test/WorkCardPlaceholderHost.svelte';

/**
 * The placeholder holds a card's place above the hero while a list loads, so
 * it must be a card's HEIGHT, and that was once only true by a browser
 * measurement. jsdom has no layout, so this pins what height is made of: the
 * frame's border and padding, the cover box's width and aspect, and every line
 * box of the text column — each carrying the same layout classes as the card's.
 * A line added to, or restyled on, one side and not the other fails here.
 */
// Every class counts EXCEPT those that cannot move a box: colour, hover and
// focus states, animation and decoration. Responsive variants (`sm:p-5`) DO
// count — only state variants are paint. A deny-list, so a new spacing or
// sizing token (`leading-*`, `py-*`, `h-*`, …) is compared by default — an
// allow-list missed exactly those.
const PAINT_ONLY =
	/^(?:(?:sm:|md:|lg:)?(?:hover|focus|focus-visible|group-hover|active):)|^(?:text-(?:text|muted|accent|gold|white)|border-border|bg-\S+|animate-\S+|opacity-\S+|transition\S*|duration-\S+|shadow\S*|no-underline)$/;
const layout = (el: Element | null | undefined) =>
	[...(el?.classList ?? [])].filter((c) => !PAINT_ONLY.test(c)).sort();

/** The frame, and the text column's line boxes in order. */
function anatomy(frame: Element) {
	const column = frame.querySelector('.self-center')!;
	return {
		frame: layout(frame),
		coverWidth: frame.firstElementChild?.classList.contains('w-14'),
		lines: [...column.children].map((line) => layout(line))
	};
}

const book: ResumeItem = {
	kind: 'book',
	slug: 'all-of-grace',
	key: 'all-of-grace',
	href: '/books/all-of-grace/3',
	title: 'All of Grace',
	author: 'C. H. Spurgeon',
	book: {
		slug: 'all-of-grace',
		title: 'All of Grace',
		language: 'en',
		subtitle: '',
		source_type: 'public_domain',
		cover_color: '#123456',
		cover_url: '/covers/art/all-of-grace.jpg',
		chapter_count: 20,
		word_count: 1000,
		author: { slug: 'spurgeon', name: 'C. H. Spurgeon', birth_year: 1834 }
	},
	pct: 13,
	order: 3,
	chapterCount: 20,
	finished: false
};
const sermon: ResumeItem = {
	kind: 'sermon',
	slug: 'power-in-prayer',
	key: 'sermon:power-in-prayer',
	href: '/sermons/power-in-prayer',
	title: 'Power in Prayer',
	author: 'R. A. Torrey',
	pct: null,
	scriptureRef: 'James 5:16',
	finished: false
};

const mounted: ReturnType<typeof mount>[] = [];
function render<P extends Record<string, unknown>>(component: Component<P>, props: P) {
	const target = document.body.appendChild(document.createElement('div'));
	mounted.push(mount(component, { target, props }));
	flushSync();
	return target;
}
afterEach(() => {
	while (mounted.length) unmount(mounted.pop()!);
	document.body.innerHTML = '';
});

describe('WorkCard placeholder', () => {
	it.each([
		['book', book],
		['sermon', sermon]
	] as const)('has the same frame and line boxes as a real %s card', (kind, item) => {
		const real = render(WorkCard, { item }).querySelector('a')!;
		const hole = render(PlaceholderHost, { kind }).querySelector(
			'[data-testid="work-card-placeholder"] > div'
		)!;
		expect(anatomy(hole)).toEqual(anatomy(real));
	});
});

describe('WorkCard caption', () => {
	it('stays one line but keeps its full text reachable', () => {
		const card = render(WorkCard, { item: sermon });
		const caption = [...card.querySelectorAll('.text-micro')].at(-1)!;
		expect(caption.classList.contains('truncate')).toBe(true);
		// The verse range survives the ellipsis, on hover and to assistive tech.
		expect(caption.getAttribute('title')).toContain('James 5:16');
	});
});
