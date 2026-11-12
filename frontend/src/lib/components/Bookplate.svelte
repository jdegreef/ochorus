<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { CoverStyleId } from '$lib/coverStyles';
	import { EX_LIBRIS, PLATE_FACES, SCRIPT_SHEET, splitAround, textScripts } from '$lib/bookplate';
	import { linkScriptFonts } from '$lib/fontSheets';
	import { i18n } from '$lib/i18n.svelte';
	import Fleuron from '$lib/components/Fleuron.svelte';

	/**
	 * An ex libris bookplate: EX LIBRIS, the house leaf, the owner's name, the
	 * book and the day it was finished. One design; the lettering is the book's
	 * own cover face (`--cover-face-<style>`), so the plate belongs to its era
	 * the way the cover does. The PNG twin is `bookplateCard.ts`.
	 *
	 * With no name (signed out, or no display name yet) the name line is left
	 * blank, as an unwritten plate is — or holds `blank`, the caller's way to
	 * fill it in.
	 */
	let {
		name,
		title,
		author,
		date,
		style,
		lang,
		compact = false,
		blank
	}: {
		name: string | null;
		title: string;
		author: string;
		date: string;
		style: CoverStyleId;
		/** The edition's language, for the title. */
		lang: string;
		/** The Bookshelf's smaller plate. */
		compact?: boolean;
		/** What stands on the name line while there is no name. */
		blank?: Snippet;
	} = $props();
	const t = i18n.t;

	const finished = $derived(splitAround(t('bookplate.finished'), '%title%'));
	const byline = $derived(t('bookplate.by').replace('%author%', author));

	// A name or title in another script than the page's: link that script's
	// faces, or the per-glyph fallback reaches a face nobody loaded.
	$effect(() => {
		for (const s of textScripts(`${name ?? ''} ${title}`)) linkScriptFonts(SCRIPT_SHEET[s]);
	});
</script>

<div
	class="plate"
	class:compact
	style:--plate-face="var(--cover-face-{style})"
	style:--plate-weight={PLATE_FACES[style].weight}
>
	<div class="plate-in">
		<p class="ex" lang="la">{EX_LIBRIS}</p>
		<Fleuron />
		{#if name}
			<p class="owner" dir="auto">{name}</p>
		{:else}
			<div class="owner-blank">{@render blank?.()}</div>
		{/if}
		<p class="words">
			{#if finished[0]}<span class="block">{finished[0]}</span>{/if}
			<span class="book" dir="auto" {lang}>{title}</span>
			{#if finished[1]}<span class="block">{finished[1]}</span>{/if}
			<span class="block" dir="auto">{byline}</span>
		</p>
		<p class="date">{date}</p>
	</div>
</div>

<style>
	/* The plate is paper in the room's light: surface, ink and the ornament
	   metal follow the theme; only the PNG has a fixed paper. */
	.plate {
		width: 100%;
		max-width: 22rem;
		margin-inline: auto;
		padding: 0.75rem;
		border-radius: 0.375rem;
		background: color-mix(in srgb, var(--gold) 7%, var(--surface));
		color: var(--text);
		box-shadow: 0 1px 2px color-mix(in srgb, var(--text) 12%, transparent);
	}
	.plate-in {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 1.5rem 1.1rem 1.25rem;
		border: 2px solid color-mix(in srgb, var(--text) 70%, transparent);
		outline: 1px solid var(--ornament);
		outline-offset: -7px;
		text-align: center;
		overflow-wrap: anywhere;
	}
	.ex,
	.owner,
	.book {
		font-family: var(--plate-face);
		font-weight: var(--plate-weight);
	}
	.ex {
		margin: 0;
		font-size: var(--fs-h2);
		letter-spacing: 0.08em;
		line-height: 1.1;
	}
	.owner {
		margin: 0.25rem 0 0;
		font-size: var(--fs-h2);
		line-height: 1.2;
		text-wrap: balance;
	}
	.owner-blank {
		width: 100%;
		margin-top: 0.25rem;
	}
	.words {
		margin: 0.5rem 0 0;
		font-family: var(--font-display);
		font-size: var(--fs-small);
		line-height: 1.45;
		color: var(--muted);
	}
	.book {
		display: block;
		margin-block: 0.15rem;
		font-size: var(--fs-h3);
		line-height: 1.25;
		color: var(--text);
		text-wrap: balance;
	}
	.date {
		margin: 0.4rem 0 0;
		font-family: var(--font-display);
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.compact .plate-in {
		gap: 0.35rem;
		padding: 1.1rem 0.85rem 0.9rem;
	}
	.compact .ex,
	.compact .owner {
		font-size: var(--fs-h3);
	}
	.compact .book {
		font-size: var(--fs-body);
	}
</style>
