<script lang="ts">
	import { palette } from '$lib/palette.svelte';
	import { PALETTES, swatchOf } from '$lib/palettes';
	import { i18n } from '$lib/i18n.svelte';
	import { theme } from '$lib/theme.svelte';
	import { radioKeys } from '$lib/radioKeys';

	/**
	 * The library-palette choice as swatch cards: each one draws its palette's
	 * own ground and colours (not the applied ones, which is the point of a
	 * preview) in the current brightness — dark swatches under the dark
	 * theme — so the reader sees what they are picking. A radio group —
	 * arrow keys move through it like any other. Used by Settings and the
	 * sign-up welcome.
	 */
	let { label }: { label: string } = $props();
	const t = i18n.t;
	const mode = $derived(theme.current === 'dark' ? 'dark' : 'light');

	const onkeydown = radioKeys(PALETTES, () => palette.current, (v) => palette.set(v), 'data-palette-option');
</script>

<div class="palettes" role="radiogroup" aria-label={label} tabindex="-1" {onkeydown}>
	{#each PALETTES as p (p)}
		{@const [ground, accent, second] = swatchOf(p, mode)}
		<button
			type="button"
			role="radio"
			aria-checked={palette.current === p}
			tabindex={palette.current === p ? 0 : -1}
			data-palette-option={p}
			class="palette"
			onclick={() => palette.set(p)}
		>
			<span class="swatch" style:background={ground} aria-hidden="true">
				<span class="bar" style:background={accent}></span>
				<span class="dot" style:background={second}></span>
			</span>
			<span class="name">{t(`palette.${p}`)}</span>
		</button>
	{/each}
</div>

<style>
	.palettes {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(6.5rem, 1fr));
		gap: 0.75rem;
	}
	.palette {
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
	.palette[aria-checked='true'] {
		border-color: var(--accent);
		box-shadow: inset 0 0 0 var(--selected-edge) var(--accent);
	}
	.swatch {
		position: relative;
		display: block;
		height: 3rem;
		border-radius: calc(var(--radius-sm) - 2px);
		box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.08);
		overflow: hidden;
	}
	.bar {
		position: absolute;
		inset-inline: 0.5rem 35%;
		bottom: 0.6rem;
		height: 0.5rem;
		border-radius: 999px;
	}
	.dot {
		position: absolute;
		top: 0.5rem;
		inset-inline-end: 0.5rem;
		width: 0.9rem;
		height: 0.9rem;
		border-radius: 50%;
	}
	.name {
		font-size: var(--fs-small);
		font-weight: 600;
		padding-inline: 0.15rem;
	}
</style>
