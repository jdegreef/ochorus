<script lang="ts">
	import { onDestroy } from 'svelte';
	import { assetHtml } from '$lib/assetUrl';
	import { markVerse } from '$lib/verse';
	import { i18n } from '$lib/i18n.svelte';
	import { getChapterExact, MODERN_EDITION, type Chapter } from '$lib/library-public';
	import { blockCount, parallelLayout, rowHeights } from '$lib/parallelReading';

	/**
	 * The right-hand column of "Side by side": the Modern English chapter beside
	 * the Original, which stays the chapter reader's own body (`original`) — so
	 * highlights, bookmarks, Listen and the saved position keep working on the
	 * element they always did. This column is read-only text.
	 *
	 * When both editions split the chapter into the same blocks
	 * (`parallelLayout`), each pair of blocks is given the height of the taller
	 * one, so paragraph N starts level with paragraph N, and hovering either
	 * lights both. When they don't, nothing is paired: this column scrolls on
	 * its own beside the Original, under a note saying why.
	 *
	 * The only marks it leaves on the Original's blocks are an inline
	 * `min-height` and the hover class — never text, so a mark's anchor (block
	 * index + character offsets) cannot move — and both go when it unmounts.
	 */
	let {
		slug,
		order,
		originalHtml,
		original
	}: {
		slug: string;
		order: number;
		/** The Original's body HTML — what the alignment decision counts. */
		originalHtml: string;
		/** The Original's rendered `.reading` element (the reader's `body`). */
		original: HTMLElement | undefined;
	} = $props();

	const t = i18n.t;

	let modern = $state<Chapter | null>(null);
	let failed = $state(false);
	let attempt = $state(0);
	let modernEl = $state<HTMLElement>();
	// The rendered blocks disagreed with the counted ones (something injected a
	// block): stop pairing rather than pair the wrong ones.
	let domMismatch = $state(false);

	$effect(() => {
		const s = slug;
		const o = order;
		void attempt;
		let live = true;
		modern = null;
		failed = false;
		domMismatch = false;
		getChapterExact(s, o, MODERN_EDITION).then(
			(c) => live && (modern = c),
			() => live && (failed = true)
		);
		return () => {
			live = false;
		};
	});

	const layout = $derived(
		modern && !domMismatch
			? parallelLayout(blockCount(originalHtml), blockCount(modern.body_html))
			: 'columns'
	);
	const rows = $derived(!!modern && layout === 'rows');

	const kids = (el: HTMLElement | undefined) => (el ? ([...el.children] as HTMLElement[]) : []);

	/** Take back what this column put on a block — down to the empty `style` /
	 *  `class` attributes, so the Original's markup is exactly as rendered. */
	function unmark(k: HTMLElement) {
		k.style.removeProperty('min-height');
		k.classList.remove('par-pair');
		if (!k.style.length) k.removeAttribute('style');
		if (!k.classList.length) k.removeAttribute('class');
	}
	function clear(el: HTMLElement | undefined) {
		kids(el).forEach(unmark);
	}

	/** Level each pair of blocks: both take the taller one's height. Reset first,
	 *  so a block that shrank (wider window, smaller text) is measured as it is. */
	function align() {
		const a = kids(original);
		const b = kids(modernEl);
		if (!rows || !a.length) return;
		if (a.length !== b.length) {
			domMismatch = true;
			clear(original);
			return;
		}
		for (const k of [...a, ...b]) k.style.removeProperty('min-height');
		const heights = rowHeights(
			a.map((k) => k.getBoundingClientRect().height),
			b.map((k) => k.getBoundingClientRect().height)
		);
		heights.forEach((h, i) => {
			a[i].style.minHeight = b[i].style.minHeight = `${h}px`;
		});
	}

	let frame = 0;
	const schedule = () => {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(align);
	};

	// Re-level whenever either column can have reflowed: a resize, the Aa panel
	// (size, face, leading, measure all resize the columns), an illustration
	// loading, a web font arriving, or the reader re-rendering the Original's
	// blocks (a new chapter, marks painted). Setting min-height is an attribute
	// change, which the MutationObserver doesn't watch — so no loop — and a
	// re-run that lands on the same heights changes no size, so the
	// ResizeObserver goes quiet.
	$effect(() => {
		const a = original;
		const b = modernEl;
		if (!rows || !a || !b) return;
		schedule();
		const ro = new ResizeObserver(schedule);
		ro.observe(a);
		ro.observe(b);
		const mo = new MutationObserver(schedule);
		mo.observe(a, { childList: true, subtree: true });
		a.addEventListener('load', schedule, true);
		b.addEventListener('load', schedule, true);
		document.fonts?.ready.then(schedule);
		return () => {
			cancelAnimationFrame(frame);
			ro.disconnect();
			mo.disconnect();
			a.removeEventListener('load', schedule, true);
			b.removeEventListener('load', schedule, true);
			clear(a);
		};
	});

	// --- The paired paragraph under the pointer or keyboard focus ------------
	let pair = $state(-1);
	/** The top-level block of `col` that `node` sits in, or -1. */
	function blockIndex(col: HTMLElement | undefined, node: EventTarget | null): number {
		let el = node instanceof Element ? node : null;
		while (el && el.parentElement !== col) el = el.parentElement;
		return el && col ? [...col.children].indexOf(el) : -1;
	}
	function track(e: Event) {
		if (!rows) return;
		const i = blockIndex(original, e.target);
		pair = i >= 0 ? i : blockIndex(modernEl, e.target);
	}
	const untrack = () => (pair = -1);

	// Listeners, not attributes: the Original is the reader's element, not ours.
	$effect(() => {
		const cols = [original, modernEl].filter((c): c is HTMLElement => !!c);
		for (const c of cols) {
			c.addEventListener('pointerover', track);
			c.addEventListener('focusin', track);
			c.addEventListener('pointerleave', untrack);
		}
		return () => {
			for (const c of cols) {
				c.removeEventListener('pointerover', track);
				c.removeEventListener('focusin', track);
				c.removeEventListener('pointerleave', untrack);
			}
		};
	});

	$effect(() => {
		const i = pair;
		if (!rows || i < 0) return;
		const cells = [kids(original)[i], kids(modernEl)[i]].filter(Boolean);
		for (const c of cells) c.classList.add('par-pair');
		return () => {
			for (const c of cells) c.classList.remove('par-pair');
		};
	});

	onDestroy(() => clear(original));
</script>

<!-- The right-hand cell of the reader's side-by-side grid (row 2, column 2). -->
<section class="par-modern" class:free={!rows} aria-label={t('reader.modernEdition')} aria-busy={!modern && !failed}>
	{#if failed}
		<div class="par-status" role="alert">
			<p>{t('reader.sideBySideError')}</p>
			<button class="btn btn-sm btn-primary mt-2" onclick={() => attempt++}>{t('shelf.retry')}</button>
		</div>
	{:else if !modern}
		<p class="par-status text-muted" role="status">{t('reader.sideBySideLoading')}</p>
	{:else}
		{#if !rows}
			<p class="par-note">{t('reader.sideBySideUnaligned')}</p>
		{/if}
		<!-- Body HTML is cleaned server-side to a safe tag subset on ingest, as the
		     Original's is; rendered the same way (verse, illustrations). -->
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="reading" bind:this={modernEl} dir="auto" lang="en">{@html assetHtml(markVerse(modern.body_html))}</div>
	{/if}
</section>

<style>
	.par-modern {
		min-width: 0;
		/* The column rule between the two texts (the grid's gap is the other half). */
		padding-inline-start: 1.5rem;
		border-inline-start: 1px solid var(--border);
	}
	/* Unpaired: this column scrolls on its own, held in view beside the
	   Original as the page scrolls. Clears the reader bar and progress foot. */
	.par-modern.free {
		position: sticky;
		top: 4.5rem;
		align-self: start;
		max-height: calc(100dvh - 9rem);
		overflow-y: auto;
		overscroll-behavior: contain;
		padding-inline-end: 0.5rem;
	}
	.par-status {
		font-size: var(--fs-small);
		padding-block: 0.5rem;
	}
	.par-note {
		margin-bottom: 1.25rem;
		padding: 0.6rem 0.8rem;
		border-inline-start: 3px solid var(--accent);
		background: var(--surface);
		border-radius: 0.375rem;
		font-size: var(--fs-small);
		color: var(--muted);
	}
	/* The paired paragraph, in both columns: a faint wash that reaches a little
	   past the text (a shadow, so it takes no room and moves nothing). */
	:global(.par-grid .reading > .par-pair) {
		background: color-mix(in srgb, var(--accent) 9%, transparent);
		box-shadow: 0 0 0 0.4rem color-mix(in srgb, var(--accent) 9%, transparent);
		border-radius: 0.25rem;
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(.par-grid .reading > *) {
			transition: background-color 120ms ease, box-shadow 120ms ease;
		}
	}
</style>
