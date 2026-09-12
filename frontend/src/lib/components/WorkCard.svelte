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
		<div class="mt-1 text-micro text-muted">
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
		class="absolute end-2 top-2 flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface-2 text-muted opacity-70 transition hover:text-accent focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
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
