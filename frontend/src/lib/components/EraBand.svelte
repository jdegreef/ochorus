<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { ERA_HUE, type EraId } from '$lib/eras';
	import type { EraCard } from '$lib/bioFacets';
	import { initials, portraitPosition, portraitSrcset } from '$lib/portraits';

	/**
	 * Two thousand years in one row: a card per church-history era with its
	 * dates, how many writers it holds, and a few of their faces. Pressing one
	 * narrows the list to that era (the Era facet, ticked from the other side);
	 * pressing it again lets go. The era's hue is the same one its writers wear
	 * on every shelf sorted by era ($lib/eras ERA_HUE).
	 *
	 * Below lg the six cards become one sideways-scrolling row, so the band
	 * costs a phone one short strip rather than a screenful.
	 */
	let {
		eras,
		selected,
		ontoggle,
		label
	}: { eras: EraCard[]; selected: string[]; ontoggle: (id: EraId) => void; label: string } = $props();

	const t = i18n.t;
</script>

<div class="era-band" role="group" aria-label={label}>
	{#each eras as e (e.id)}
		{@const on = selected.includes(e.id)}
		<button
			type="button"
			class="era-card"
			class:on
			class:dim={e.count === 0 && !on}
			style="--hue: {ERA_HUE[e.id]}"
			aria-pressed={on}
			onclick={() => ontoggle(e.id)}
		>
			<span class="font-display era-name">{e.name}</span>
			{#if e.range}<span class="era-range">{e.range}</span>{/if}
			<span class="era-foot">
				<span class="era-faces" aria-hidden="true">
					{#each e.faces as a (a.slug)}
						{#if a.photo_url}
							{@const source = { src: a.photo_url, srcset: portraitSrcset(a.photo_url) }}
							<img
								src={source.src}
								srcset={source.srcset}
								use:hydrateSrc={source}
								sizes="28px"
								width="28"
								height="28"
								alt=""
								loading="eager"
								style="object-position: {portraitPosition(a.slug)}"
							/>
						{:else}
							<span class="era-initials">{initials(a.name)}</span>
						{/if}
					{/each}
				</span>
				<span class="era-count">{e.count}<span class="sr-only"> {t(e.count === 1 ? 'common.authorOne' : 'common.authorMany')}</span></span>
			</span>
		</button>
	{/each}
</div>

<style>
	.era-band {
		/* The scroller is the containing block for anything absolute inside it
		   (the counts' sr-only labels). Unpositioned, the last card's label
		   resolved against the page, ~965px across, and a phone laid the whole
		   page out at that width — zoomed out, the fixed tab bar 970px wide. */
		position: relative;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(9.5rem, 1fr);
		gap: 0.6rem;
		overflow-x: auto;
		/* Room for the focus ring and the scrollbar on a phone. */
		padding: 0.15rem 0.15rem 0.5rem;
		scrollbar-width: none;
	}
	.era-card {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.15rem;
		text-align: start;
		background: var(--surface);
		border: 1px solid var(--border);
		border-top: 4px solid var(--hue);
		border-radius: var(--radius-card);
		padding: 0.75rem 0.8rem 0.65rem;
		cursor: pointer;
		color: var(--text);
		transition:
			background var(--duration-base, 150ms),
			border-color var(--duration-base, 150ms);
	}
	.era-card:hover {
		background: color-mix(in srgb, var(--hue) 7%, var(--surface));
	}
	.era-card.on {
		background: color-mix(in srgb, var(--hue) 12%, var(--surface));
		border-color: color-mix(in srgb, var(--hue) 55%, var(--border));
		border-top-color: var(--hue);
	}
	.era-card.dim {
		opacity: 0.55;
	}
	.era-name {
		font-size: var(--fs-small);
		font-weight: 600;
		line-height: 1.25;
	}
	.era-range {
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.era-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		margin-top: auto;
		padding-top: 0.55rem;
	}
	.era-faces {
		display: flex;
	}
	.era-faces > * {
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 999px;
		border: 2px solid var(--surface);
		margin-inline-end: -0.45rem;
		object-fit: cover;
		filter: grayscale(1);
	}
	.era-card:hover .era-faces > img,
	.era-card.on .era-faces > img {
		filter: none;
	}
	.era-initials {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: color-mix(in srgb, var(--hue) 22%, var(--surface));
		color: var(--text);
		font-size: var(--fs-micro);
		font-weight: 700;
		letter-spacing: -0.04em;
	}
	.era-count {
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	@media (min-width: 1024px) {
		.era-band {
			grid-auto-flow: row;
			grid-template-columns: repeat(6, minmax(0, 1fr));
			overflow: visible;
		}
	}
</style>
