<script lang="ts">
	import type { SermonSummary } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime, preachedYear } from '$lib/reading';
	import SermonMonogram from '$lib/components/SermonMonogram.svelte';
	import { hueForBirthYear } from '$lib/eras';

	/**
	 * A sermon on a SHELF — the one card for "here is a sermon, go read it".
	 *
	 * Not every mention of a sermon: the resume tile in Continue reading is a
	 * progress row, Sermon of the week is a feature panel, and prev/next on a
	 * sermon page is navigation. Those are different jobs. This is the one that
	 * lists sermons to choose between.
	 *
	 * There were three: this card (topics), a `sermonRow` snippet living inside
	 * the sermons index, and a hand-rolled list on the author page that computed
	 * its own reading time with `Math.round(word_count / 200)` rather than the
	 * shared `readingTime()`. The same sermon therefore had three different
	 * lengths of metadata and, on the author page, a length that could disagree
	 * with the one on its own page.
	 *
	 * Two variants, the same pair Books already has (`BookCard` / `BookListRow`):
	 *
	 *   - `card` — compact, for a grid beside other content (a topic's sermons,
	 *     an author's sermons).
	 *   - `row` — full width, with the era rail, the era-tinted passage monogram and a
	 *     two-line preview of the brief, for the sermons index where sermons ARE
	 *     the content.
	 *
	 * `.sermon-row*` is styled globally in app.css; only `card` carries scoped
	 * styles here.
	 */
	let {
		sermon,
		showAuthor = false,
		variant = 'card'
	}: {
		sermon: SermonSummary;
		/** Name the preacher. The index turns this off when a heading already does. */
		showAuthor?: boolean;
		variant?: 'card' | 'row';
	} = $props();
	const t = i18n.t;
	/** Empty for a sermon with no recorded date — the row drops the "· 1857". */
	const year = $derived(preachedYear(sermon.preached_on));
	const href = $derived(localizeHref(`/sermons/${sermon.slug}`));

	// The index row reads like a table of contents with a preview: one line per
	// sermon, then the first two lines of its brief, always shown — the brief is
	// what a reader chooses by, and two lines fill space the row had anyway. The
	// chevron opens the rest of it; a brief that fits in two lines has no rest,
	// so it gets no chevron. (`row` only.)
	let open = $state(false);
	const briefId = $derived(`sermon-brief-${sermon.slug}`);
	// Assume a long brief until measured: prerendered HTML keeps the chevron (and
	// its keyboard path), and the client drops it where the brief fits.
	let clipped = $state(true);
	const expandable = $derived(!!sermon.summary && clipped);
	let briefEl = $state<HTMLParagraphElement>();
	$effect(() => {
		if (!briefEl) return;
		// An open brief isn't clamped, so it can't say whether it would be; the
		// observer re-measures when it closes. `open` is read untracked so a
		// toggle doesn't tear down and rebuild the observer.
		const measure = () => {
			if (!untrack(() => open)) clipped = briefEl!.scrollHeight > briefEl!.clientHeight + 1;
		};
		measure();
		const ro = new ResizeObserver(measure);
		ro.observe(briefEl);
		return () => ro.disconnect();
	});

	// Two-stage click on the row body (a pointer convenience): the title link and
	// the chevron keep their own jobs, but a click ANYWHERE else first opens a
	// clipped brief in full, then goes to the sermon on the next click. A row with
	// nothing more to show goes straight there. Keyboard users reach both actions
	// directly — the title link navigates, the chevron toggles — so this handler
	// on a static element is an enhancement, not the only path.
	function onRowClick(event: MouseEvent) {
		if ((event.target as HTMLElement).closest('a, button')) return;
		if (expandable && !open) {
			open = true;
			return;
		}
		goto(href);
	}
</script>

{#if variant === 'row'}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div
		class="sermon-row card-tint group"
		class:is-open={open}
		onclick={onRowClick}
		style="--row-hue: {hueForBirthYear(sermon.author.birth_year)}"
	>
		<!-- Every sermon opens with its passage as a monogram (MAT over 11), in
		     the era tint. It replaced illustrated emblems, which repeated: most
		     sermons drew theirs from a small hashed fallback pool. -->
		<SermonMonogram class="sermon-row-monogram" scriptureRef={sermon.scripture_ref} title={sermon.title} />
		<div class="min-w-0 flex-1">
			<!-- One table-of-contents line: the title is the link to the sermon (a
			     real, crawlable anchor per row); the passage, a dotted leader and the
			     length follow; a chevron opens the brief below in full — only when
			     it runs past two lines. The <h3> keeps the title's heading semantics. -->
			<div class="sermon-row-line">
				<h3 class="sermon-row-heading">
					<a class="sermon-row-title" {href}>{sermon.title}</a>
				</h3>
				<span class="sermon-row-ref"
					>{#if showAuthor}{sermon.author.name}<span class="opacity-40"> · </span>{/if}{sermon.scripture_ref}</span
				>
				<span class="sermon-row-leader hidden sm:block" aria-hidden="true"></span>
				<span class="sermon-row-meta"
					>{readingTime(sermon.word_count)}{#if year}<span class="opacity-50"> · </span>{year}{/if}</span
				>
				{#if expandable}
					<button
						type="button"
						class="sermon-row-toggle"
						aria-label={t('sermon.inBrief')}
						aria-expanded={open}
						aria-controls={briefId}
						onclick={() => (open = !open)}
					>
						<svg
							class="sermon-row-chevron"
							viewBox="0 0 24 24"
							width="20"
							height="20"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg
						>
					</button>
				{/if}
			</div>
			{#if sermon.summary}
				<p id={briefId} class="sermon-row-brief" class:line-clamp-2={!open} bind:this={briefEl}>
					{sermon.summary}
				</p>
			{/if}
		</div>
	</div>
{:else}
	<a
		class="sermon-card card-tint rounded-card border border-border bg-surface"
		href={localizeHref(`/sermons/${sermon.slug}`)}
	>
		<SermonMonogram class="monogram" scriptureRef={sermon.scripture_ref} title={sermon.title} />
		<span class="min-w-0 flex-1">
			<span class="eyebrow sermon-label">{t('sermons.label')}</span>
			<span class="title">{sermon.title}</span>
			{#if showAuthor}
				<span class="author">{sermon.author.name}</span>
			{/if}
			<span class="meta">
				{#if sermon.scripture_ref}<span class="ref">{sermon.scripture_ref}</span>{/if}
				<span class="time">{readingTime(sermon.word_count)}</span>
			</span>
		</span>
	</a>
{/if}

<style>
	/* Row card. Only layout + padding are scoped; the resting frame (border,
	   radius, ground) rides on layered Tailwind utilities in the markup and the
	   hover (border→accent, ground→surface-2, no lift) on the shared .card-tint
	   — both unlayered/layered, so neither ties this scoped rule and the hover
	   always wins. */
	.sermon-card {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.85rem 1rem;
	}
	/* The sermon's monogram chip (recipe in app.css) — only size and hue here. */
	.sermon-card :global(.monogram) {
		--chip-size: 3rem;
		--chip-hue: var(--color-accent);
	}
	.sermon-label {
		display: inline-block;
		font-size: var(--fs-micro);
		color: var(--color-accent);
	}
	.title {
		display: block;
		font-weight: 600;
		line-height: 1.3;
		color: var(--color-text);
	}
	.author {
		display: block;
		font-size: var(--fs-small);
		color: var(--color-muted);
		margin-top: 0.1rem;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
		margin-top: 0.35rem;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.ref {
		color: var(--color-accent);
	}
</style>
