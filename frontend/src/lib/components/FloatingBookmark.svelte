<script lang="ts">
	/**
	 * Bookmark the spot, from a button that FLOATS in the bottom corner — for a
	 * Reader surface whose header scrolls away (a biography, an article). A
	 * header control there can only be reached by scrolling back to the top, at
	 * which point "the paragraph at the top of the viewport" is paragraph one,
	 * every time: it would look right and save the wrong place on every click.
	 * (The sermon keeps its Bookmark in its sticky bar, which never leaves.)
	 *
	 * Shown only while the prose is in view (`frac` inside the text): both pages
	 * continue past it — books, contemporaries, related reading — and a bookmark
	 * control has nothing to point at once the text is behind you.
	 */
	import Icon from '$lib/components/Icon.svelte';
	import { i18n } from '$lib/i18n.svelte';

	let {
		bookmark,
		frac
	}: {
		/** From `readerBookmark` — the paragraph at the top of the screen. */
		bookmark: { readonly current: boolean; toggle(): void };
		/** The Reader's progress through the prose, 0–1. */
		frac: number;
	} = $props();

	const t = i18n.t;
</script>

{#if frac > 0.01 && frac < 0.99}
	<button
		class="float-bookmark"
		class:is-set={bookmark.current}
		onclick={bookmark.toggle}
		aria-label={t('reader.bookmark')}
		title={t('reader.bookmark')}
		aria-pressed={bookmark.current}><Icon name="bookmark" size={18} /></button
	>
{/if}

<style>
	/* Mirrors `.min-left` (app.css) — same corner treatment, z-index and
	   translucency — so the pills that appear while reading read as one family.
	   At the inline end, not centred: `.min-left` owns the centre and this one is
	   tappable. It clears whichever bottom bar is up, as the PWA toasts do — the
	   phone tab bar (z-40) used to sit on top of it and take the tap. Logical
	   properties throughout: Arabic is a routed locale. */
	.float-bookmark {
		position: fixed;
		bottom: calc(
			1rem + max(env(safe-area-inset-bottom) + var(--listenbar-h, 0px), var(--tabbar-h, 0px))
		);
		inset-inline-end: 1rem;
		z-index: 30;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 9999px;
		border: 1px solid var(--border);
		background: color-mix(in srgb, var(--bg) 85%, transparent);
		backdrop-filter: blur(6px);
		color: var(--muted);
	}
	.float-bookmark:hover {
		color: var(--text);
	}
	.float-bookmark.is-set {
		color: var(--accent);
		border-color: var(--accent);
	}
</style>
