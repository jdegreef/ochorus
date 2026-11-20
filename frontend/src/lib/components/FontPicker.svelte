<script lang="ts">
	import { readerPrefs, fontLabel, FONT_STACK, READER_FONTS, type ReaderFont } from '$lib/readerPrefs.svelte';
	import { READER_FONTS_SHEET, linkSheet } from '$lib/fontSheets';
	import { i18n } from '$lib/i18n.svelte';
	import { radioKeys } from '$lib/radioKeys';
	import { onMount } from 'svelte';

	/**
	 * The reading face as cards, each an "Aa" set in that face with its name
	 * beneath: a typeface is chosen by looking at it (ReaderControls' typeface
	 * buttons do the same). Most faces live in their own sheet
	 * ($lib/fontSheets), linked as this mounts — nothing loads until Settings'
	 * Appearance section is open, and each face's latin file only once drawn.
	 */
	let { label }: { label: string } = $props();
	const t = i18n.t;
	const kinds = {
		serif: t('settings.fontSerif'),
		sans: t('settings.fontSans'),
		dyslexic: t('settings.fontDyslexic')
	};
	onMount(() => linkSheet(READER_FONTS_SHEET));
	const onkeydown = radioKeys<ReaderFont>(
		READER_FONTS,
		() => readerPrefs.font,
		(v) => readerPrefs.setFont(v),
		'data-font-option'
	);
</script>

<div class="faces" role="radiogroup" aria-label={label} tabindex="-1" {onkeydown}>
	{#each READER_FONTS as f (f)}
		<button
			type="button"
			role="radio"
			aria-checked={readerPrefs.font === f}
			tabindex={readerPrefs.font === f ? 0 : -1}
			data-font-option={f}
			class="face"
			onclick={() => readerPrefs.setFont(f)}
		>
			<span class="aa" style:font-family={FONT_STACK[f]} aria-hidden="true">Aa</span>
			<span class="name">{fontLabel(f, kinds)}</span>
		</button>
	{/each}
</div>

<style>
	.faces {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(6.5rem, 1fr));
		gap: 0.6rem;
	}
	.face {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
		padding: 0.55rem 0.4rem 0.45rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--text);
		cursor: pointer;
		min-inline-size: 0;
	}
	.face[aria-checked='true'] {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.face:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.aa {
		font-size: var(--fs-h2);
		line-height: 1.1;
	}
	.name {
		font-size: var(--fs-small);
		color: var(--muted);
		max-inline-size: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.face[aria-checked='true'] .name {
		color: var(--accent);
		font-weight: 600;
	}
</style>
