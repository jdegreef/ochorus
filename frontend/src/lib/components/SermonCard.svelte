<script lang="ts">
	import type { SermonSummary } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { readingTime, preachedYear } from '$lib/reading';
	import SermonMonogram from '$lib/components/SermonMonogram.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { hueForBirthYear } from '$lib/eras';

	/**
	 * A sermon on a SHELF — the one card for "here is a sermon, go read it".
	 *
	 * Not every mention of a sermon: the resume tile in Continue reading is a
	 * progress row, Sermon of the day is a feature panel, and prev/next on a
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
	 * The card opens with the preacher's face, printed as a duotone in the
	 * sermons hue (`.duotone`, app.css), when it names the preacher and there
	 * is a portrait — a face is what a reader recognises a sermon by before its
	 * title. Otherwise, and always where the page already belongs to one
	 * preacher (their author page, `showAuthor` off), the passage monogram:
	 * the same face on every card there would say nothing.
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
		// A clamped box stays two lines tall whatever overflows it, so the
		// observer misses a reflow that only changes how much is hidden — the
		// web font swapping in is the one that matters (a brief that fit in the
		// fallback face can overflow in the real one).
		document.fonts?.ready.then(measure);
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
						<Icon name="chevron-right" size={22} strokeWidth={2.25} class="sermon-row-chevron" mirror={false} />
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
		{#if showAuthor && sermon.author.photo_url}
			<span class="monogram emblem-chip duotone">
				<Portrait
					slug={sermon.author.slug}
					name={sermon.author.name}
					url={sermon.author.photo_url}
					px={48}
					decorative
					tone="color"
					class="h-full w-full"
				/>
			</span>
		{:else}
			<SermonMonogram class="monogram" scriptureRef={sermon.scripture_ref} title={sermon.title} />
		{/if}
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
	/* The sermon row's parts (monogram, passage, title, leader, toggle, brief),
	   moved out of app.css: only this component wears them (INP — a smaller
	   site-wide sheet). :global keeps selectors and specificity as they were;
	   the shared .sermon-row box (the /quotes card borrows it) stays in app.css. */
	:global {
		/* The sermon's passage monogram (SermonMonogram), in the writer's era tint, so
		   each row opens with its own mark rather than a wall of prose. */
		.sermon-row-monogram {
			--chip-size: 3.25rem;
			--chip-hue: var(--row-hue);
		}
		/* The passage the sermon expounds — an eyebrow, in the era tint. */
		.sermon-row-ref {
			font-size: var(--fs-eyebrow);
			font-weight: 600;
			letter-spacing: 0.08em;
			text-transform: uppercase;
			color: color-mix(in srgb, var(--row-hue) 42%, var(--text));
		}
		.sermon-row-title {
			font-family: var(--font-display);
			font-size: var(--fs-h3);
			font-weight: 600;
			line-height: 1.3;
			color: var(--text);
			transition: color var(--duration-fast);
		}
		.sermon-row:hover .sermon-row-title {
			color: color-mix(in srgb, var(--row-hue) 70%, var(--text));
		}
		/* ── Sermon index: table-of-contents row ─────────────────────────────────────
		   The row reads like a book's contents: one line per sermon (title · passage ·
		   a dotted leader · length), then a two-line preview of the brief that the
		   chevron opens in full. The emblem + content flex layout of `.sermon-row`
		   above is unchanged; what follows styles the one-line entry and the brief. */

		/* Heading wraps the toggle (WAI accordion pattern); it carries no visual weight
		   of its own — the title span inside does. */
		.sermon-row-heading {
			margin: 0;
			font-size: inherit;
			font-weight: inherit;
		}
		/* The title is the link to the sermon — a real, crawlable anchor on every row.
		   Row-hover already recolours it (rule above); a direct hover underlines. */
		a.sermon-row-title {
			text-decoration: none;
		}
		a.sermon-row-title:hover {
			text-decoration: underline;
		}
		/* Title, passage, leader and length on one baseline; wraps gracefully when the
		   title is long. */
		.sermon-row-line {
			display: flex;
			flex-wrap: wrap;
			align-items: baseline;
			gap: 0.25rem 0.75rem;
		}
		/* The dotted leader carrying the eye from the title to the length, as in a
		   printed table of contents — purely decorative, and it simply collapses to its
		   min width when the line wraps. */
		.sermon-row-leader {
			flex: 1 1 1.5rem;
			min-width: 1.5rem;
			align-self: baseline;
			border-bottom: 1.5px dotted color-mix(in srgb, var(--row-hue) 32%, var(--border-strong));
			transform: translateY(-0.3em);
		}
		.sermon-row-meta {
			flex: none;
			font-size: var(--fs-small);
			color: var(--muted);
			font-variant-numeric: tabular-nums;
		}
		/* The disclosure control for the brief — a chevron button beside the length,
		   kept separate from the title link so each control has a single job. */
		.sermon-row-toggle {
			flex: none;
			align-self: center;
			display: inline-flex;
			align-items: center;
			justify-content: center;
			/* A 32px target with a visible ring on hover, so it reads as a control and
			   not a stray mark at the end of the leader (QA, 2026-10); coarse pointers
			   still grow to 44px below. */
			min-width: 2rem;
			min-height: 2rem;
			padding: 0.2rem;
			border: 0;
			background: none;
			color: var(--muted);
			cursor: pointer;
			border-radius: var(--radius-sm);
		}
		.sermon-row-toggle:hover {
			color: var(--text);
			background: var(--surface-2);
		}
		.sermon-row-toggle:focus-visible {
			outline: 2px solid var(--accent);
			outline-offset: 1px;
		}
		/* The shared chevron-right, turned down (closed) / up (open) like QandA's —
		   a rotation, so it needs no RTL flip. */
		.sermon-row-chevron {
			display: block;
			transform: rotate(90deg);
			transition: transform var(--duration-fast);
		}
		.sermon-row.is-open .sermon-row-chevron {
			transform: rotate(-90deg);
		}
		/* The brief under the entry: always there as a two-line preview (what a reader
		   chooses by; the clamp is `line-clamp-2` in the markup, lifted while open). It
		   hangs in the content column (already inset past the emblem) at a reading
		   measure, not the full row width. */
		.sermon-row-brief {
			margin: 0.4rem 0 0;
			max-width: 64ch;
			color: var(--muted);
		}
	}

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
		--chip-hue: var(--section-sermons);
		--duotone-hue: var(--section-sermons);
	}
	.sermon-label {
		display: inline-block;
		font-size: var(--fs-micro);
		color: var(--section-sermons);
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
