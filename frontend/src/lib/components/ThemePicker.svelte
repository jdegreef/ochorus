<script lang="ts">
	import { theme, THEME_OPTIONS, type ThemePref } from '$lib/theme.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { radioKeys } from '$lib/radioKeys';

	/**
	 * The theme choice as little pages: each card is drawn in its own
	 * brightness — the page ground, three lines of text and an accent rule — so
	 * a reader picks Sepia by seeing sepia, as PalettePicker does for the
	 * library colours. System is the light page and the dark page split
	 * corner to corner, because it is whichever of the two the device asks for.
	 *
	 * The colours are the themes' own grounds and inks from app.css
	 * (`:root`, `[data-theme='sepia']`, `[data-theme='dark']`) under the default
	 * palette. They are drawn literally, not read from the tokens, because the
	 * tokens hold the APPLIED theme: a card that read them would show the
	 * current look four times. (hex-ok-file: this component paints the themes'
	 * own colours, which is its whole job.)
	 */
	let { label }: { label: string } = $props();
	const t = i18n.t;

	const LOOK: Record<Exclude<ThemePref, 'system'>, { ground: string; ink: string; rule: string }> = {
		light: { ground: '#faf6ef', ink: '#221c15', rule: '#3f3d9a' },
		sepia: { ground: '#f4ecd8', ink: '#40331f', rule: '#3f3d9a' },
		dark: { ground: '#16130f', ink: '#ece3d4', rule: '#9c9af2' }
	};
	const VALUES = THEME_OPTIONS.map((o) => o.v);
	const onkeydown = radioKeys(VALUES, () => theme.preference, (v) => theme.set(v), 'data-theme-option');
</script>

<div class="themes" role="radiogroup" aria-label={label} tabindex="-1" {onkeydown}>
	{#each THEME_OPTIONS as o (o.v)}
		{@const look = o.v === 'system' ? null : LOOK[o.v]}
		<button
			type="button"
			role="radio"
			aria-checked={theme.preference === o.v}
			tabindex={theme.preference === o.v ? 0 : -1}
			data-theme-option={o.v}
			class="theme"
			onclick={() => theme.set(o.v)}
		>
			<span
				class="page"
				class:split={!look}
				style:--ground={look?.ground}
				style:--ink={look?.ink}
				style:--rule={look?.rule}
				aria-hidden="true"
			>
				{#if !look}
					<span class="half" style:--ground={LOOK.dark.ground} style:--ink={LOOK.dark.ink}></span>
				{/if}
				<span class="rule"></span>
				<span class="line"></span>
				<span class="line"></span>
				<span class="line short"></span>
			</span>
			<span class="name">{t(o.k)}</span>
		</button>
	{/each}
</div>

<style>
	.themes {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(6.5rem, 1fr));
		gap: 0.75rem;
	}
	.theme {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		padding: 0.4rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--text);
		text-align: start;
		cursor: pointer;
	}
	.theme[aria-checked='true'] {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.theme:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.page {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 0.28rem;
		block-size: 3.6rem;
		padding: 0.55rem 0.6rem;
		border-radius: 4px;
		overflow: hidden;
		background: var(--ground, #faf6ef);
		--ground: #faf6ef;
		--ink: #221c15;
		--rule: #3f3d9a;
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ink) 12%, transparent);
	}
	/* System: the dark page drawn over the lower-right half of the light one. */
	.half {
		position: absolute;
		inset: 0;
		background: var(--ground);
		clip-path: polygon(100% 0, 100% 100%, 0 100%);
	}
	.rule,
	.line {
		position: relative;
		display: block;
		block-size: 3px;
		border-radius: 2px;
	}
	.rule {
		inline-size: 35%;
		background: var(--rule);
	}
	.line {
		inline-size: 90%;
		background: color-mix(in srgb, var(--ink) 55%, transparent);
	}
	.line.short {
		inline-size: 60%;
	}
	/* On the split card the lines cross both halves: draw them in a mid ink
	   that reads on either ground. */
	.split .line {
		background: #8a7f70;
	}
	.name {
		font-size: var(--fs-small);
		font-weight: 600;
		padding-inline: 0.15rem;
	}
</style>
