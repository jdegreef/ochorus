<script lang="ts" module>
	/**
	 * A card-shaped placeholder, for a list that knows a card is coming but not
	 * yet what it holds ("Continue reading" above the hero, while a list loads).
	 * It lives HERE, beside the card, and draws the card's own frame and line
	 * boxes — the same border and padding, the same w-14 3:4 cover box, the
	 * title/author/caption lines at their real sizes and the real ProgressBar —
	 * so it is the card's height by construction, not by a measurement someone
	 * has to keep in step. A sermon card has no meter, so neither does its
	 * placeholder.
	 */
	export { placeholder };
</script>

<script lang="ts">
	import BookCover from '$lib/components/BookCover.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { offerFinish, unmarkFinished } from '$lib/progress';
	import type { ResumeItem } from '$lib/resumeItems';

	/**
	 * One resume card: a cover (books) or a soft mic tile (sermons), the title and
	 * author, and either a chapter meter or the sermon's reference line. Shared by
	 * the home "Continue reading" strip and the /reading page so a resume card is
	 * drawn in exactly one place.
	 *
	 * `complete` is the /reading "Finished" variant — it drops the progress meter
	 * (a full bar under a "Finished" heading says nothing) and marks the line with
	 * a gold check. The strip never passes it, so its cards are unchanged.
	 *
	 * A corner button lets the reader finish a work (or, on a finished card,
	 * un-finish it) without reopening — faint until the card is hovered or the
	 * button focused, always reachable on touch. `offerFinish` shows a short Undo;
	 * the lists re-derive off the `ochorus:sync` it dispatches, so the card moves
	 * on its own.
	 */
	let { item, complete = false }: { item: ResumeItem; complete?: boolean } = $props();
	const t = i18n.t;

	function toggleFinished(e: Event) {
		e.preventDefault();
		if (complete) unmarkFinished(item.slug, item.kind);
		else offerFinish(item.slug, item.kind);
	}

	// The caption under the title, composed here (the single render site) from the
	// item's structured fields: a sermon's reference, a finished tally, or the
	// chapter meter. So the strip and /reading can't word it two ways.
	const caption = $derived.by(() => {
		if (item.kind === 'sermon') {
			return item.scriptureRef
				? `${t('search.typeSermon')} · ${item.scriptureRef}`
				: t('search.typeSermon');
		}
		if (complete) return `${t('settings.statFinished')} · ${item.order} / ${item.chapterCount}`;
		return `${t('continue.chapter')} ${item.order} / ${item.chapterCount} · ${item.pct}%`;
	});
</script>

{#snippet placeholder(kind: 'book' | 'sermon')}
	<div class="group relative" aria-hidden="true" data-testid="work-card-placeholder">
		<div class="flex gap-4 rounded-card border border-border p-4">
			<div class="aspect-[3/4] w-14 shrink-0 animate-pulse rounded-sm bg-surface-2"></div>
			<div class="min-w-0 flex-1 self-center">
				<div class="truncate text-small font-semibold">
					<span class="inline-block w-3/4 animate-pulse rounded bg-surface-2">&nbsp;</span>
				</div>
				<div class="mt-0.5 truncate text-small">
					<span class="inline-block w-1/2 animate-pulse rounded bg-surface-2">&nbsp;</span>
				</div>
				{#if kind === 'book'}
					<div class="mt-2"><ProgressBar percent={0} label="" /></div>
				{/if}
				<div class="mt-1 truncate text-micro">&nbsp;</div>
			</div>
		</div>
	</div>
{/snippet}

<div class="group relative">
<a
	href={localizeHref(item.href)}
	class="flex gap-4 rounded-card border border-border p-4 hover:bg-surface-2 hover:no-underline"
>
	{#if item.book}
		<!-- Draw through BookCover, not a bare <img>: a plate (SVG) ground carries
		     no title in the file, so a raw image shows a blank coloured tile —
		     BookCover sets the title over it, as the shelves do. -->
		<div class="w-14 shrink-0">
			<BookCover book={item.book} rounded="rounded-sm" />
		</div>
	{:else}
		<!-- Sermons have no cover; a soft mic tile (matching SermonCard's visual
		     language) reads as intentional, not a blank block. -->
		<div
			class="sermon-thumb flex aspect-[3/4] w-14 shrink-0 items-center justify-center rounded-sm border shadow-sm"
		>
			<Icon name="mic" size={22} />
		</div>
	{/if}
	<div class="min-w-0 flex-1 self-center">
		<div class="truncate text-small font-semibold text-text">{item.title}</div>
		<div class="mt-0.5 truncate text-small text-muted">{item.author}</div>
		{#if item.pct !== null && !complete}
			<div class="mt-2">
				<ProgressBar percent={item.pct} label="{item.title}: {caption}" />
			</div>
		{/if}
		<!-- One line, like the title and author: a translated caption wrapping on a
		     narrow card would make the card taller than its placeholder. The full
		     text stays reachable in `title` — on /reading a sermon's verse range
		     is worth the hover. -->
		<div class="mt-1 truncate text-micro text-muted" title={caption}>
			{#if complete}<span class="text-gold" aria-hidden="true">✓</span> {/if}{caption}
		</div>
	</div>
</a>
	<!-- Finish (or un-finish, on a completed card) without reopening. Faint until
	     the card is hovered or the button focused; always reachable on touch. -->
	<button
		type="button"
		onclick={toggleFinished}
		title={complete ? t('settings.unfinish') : t('continue.markFinished')}
		aria-label="{complete ? t('settings.unfinish') : t('continue.markFinished')}: {item.title}"
		class="finish-btn absolute end-2 top-2 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface-2 text-muted opacity-70 transition hover:text-accent focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
	>
		<Icon name={complete ? 'skip-back' : 'check'} size={15} />
	</button>
</div>

<style>
	/* Sermon thumbnail: a soft, accent-tinted tile with the mic glyph, sized to
	   the same footprint as book covers. Theme-aware via the shared tokens. */
	.sermon-thumb {
		color: var(--color-accent);
		border-color: var(--color-accent-soft-border);
		background: linear-gradient(155deg, var(--color-accent-soft), var(--color-surface-2));
	}
</style>
