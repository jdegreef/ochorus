<script lang="ts">
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import { i18n } from '$lib/i18n.svelte';
	import type { BandCard } from '$lib/bioFacets';
	import Portrait from '$lib/components/Portrait.svelte';

	/**
	 * A browse lens on the biographies index: one card per era, tradition or
	 * region, each with a short line beneath its name (the era's dates, the
	 * tradition's best-known writers), a few faces and how many writers it
	 * holds under the other filters. Pressing a card ticks that value of its
	 * facet — the same tick the toolbar menus make — and pressing it again lets
	 * go. A region card also carries its places as chips, each its own tick.
	 *
	 * `hue` tints a card (an era's colour, the same one its writers wear on every
	 * shelf sorted by era); a card without one uses the accent.
	 *
	 * Below lg the cards become one sideways-scrolling row, so the band costs a
	 * phone one short strip rather than a screenful; from lg they sit in a grid
	 * of `cols` columns.
	 */
	let {
		cards,
		selected,
		ontoggle,
		label,
		cols = 6
	}: {
		cards: BandCard[];
		/** The facet's ticked values (cards and their children alike). */
		selected: string[];
		ontoggle: (id: string) => void;
		label: string;
		cols?: number;
	} = $props();

	const t = i18n.t;
	const authors = (n: number) => t(n === 1 ? 'common.authorOne' : 'common.authorMany');
</script>

{#snippet face(c: BandCard)}
	<span class="font-display band-name">{c.name}</span>
	{#if c.sub}<span class="band-sub">{c.sub}</span>{/if}
	<span class="band-foot">
		<span class="band-faces" aria-hidden="true">
			{#each c.faces as a (a.slug)}
				<Portrait
					slug={a.slug}
					name={a.name}
					url={a.photo_url}
					px={28}
					decorative
					loading="eager"
					initialsClass="band-initials"
				/>
			{/each}
		</span>
		<span class="band-count">{c.count}<span class="sr-only"> {authors(c.count)}</span></span>
	</span>
{/snippet}

<!-- A band with child chips (regions) gets wider phone cards, so a region's
     places sit side by side rather than one per line. -->
<div
	class="band"
	use:scrollEdges
	role="group"
	aria-label={label}
	style="--cols: {cols}; --card-min: {cards.some((c) => c.children?.length) ? '15rem' : '9.5rem'}"
>
	{#each cards as c (c.id)}
		{@const on = selected.includes(c.id)}
		{#if c.children?.length}
			<!-- A region: the card's head is its own tick; each place beneath it
			     is a chip with its own. Buttons can't nest, so this card is a div. -->
			{@const kidOn = c.children.some((k) => selected.includes(k.id))}
			<!-- Never faded while one of its places is the live filter. -->
			<div class="band-card" class:on class:dim={c.count === 0 && !on && !kidOn} style:--hue={c.hue}>
				<button type="button" class="band-body band-head" aria-pressed={on} onclick={() => ontoggle(c.id)}>
					{@render face(c)}
				</button>
				<span class="band-kids">
					{#each c.children as k (k.id)}
						{@const kon = selected.includes(k.id)}
						<button
							type="button"
							class="band-kid"
							class:on={kon}
							aria-pressed={kon}
							onclick={() => ontoggle(k.id)}
							>{k.name}<span class="band-kid-n">{k.count}</span></button
						>
					{/each}
				</span>
			</div>
		{:else}
			<button
				type="button"
				class="band-card band-body"
				class:on
				class:dim={c.count === 0 && !on}
				style:--hue={c.hue}
				aria-pressed={on}
				onclick={() => ontoggle(c.id)}
			>
				{@render face(c)}
			</button>
		{/if}
	{/each}
</div>

<style>
	.band {
		/* The scroller is the containing block for anything absolute inside it
		   (the counts' sr-only labels). Unpositioned, the last card's label
		   resolved against the page, ~965px across, and a phone laid the whole
		   page out at that width — zoomed out, the fixed tab bar 970px wide. */
		position: relative;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(var(--card-min, 9.5rem), 1fr);
		gap: 0.6rem;
		overflow-x: auto;
		/* Room for the focus ring and the scrollbar on a phone. */
		padding: 0.15rem 0.15rem 0.5rem;
		scrollbar-width: none;
		/* Fade an edge while cards hide past it (`use:scrollEdges`): with no
		   scrollbar, a tablet with a trackpad had no sign there was more. */
		--fade-s: 0rem;
		--fade-e: 0rem;
		-webkit-mask-image: linear-gradient(to right, transparent, black var(--fade-s), black calc(100% - var(--fade-e)), transparent);
		mask-image: linear-gradient(to right, transparent, black var(--fade-s), black calc(100% - var(--fade-e)), transparent);
	}
	.band:global(.more-start) {
		--fade-s: 1.5rem;
	}
	.band:global(.more-end) {
		--fade-e: 1.5rem;
	}
	:global([dir='rtl']) .band {
		-webkit-mask-image: linear-gradient(to left, transparent, black var(--fade-s), black calc(100% - var(--fade-e)), transparent);
		mask-image: linear-gradient(to left, transparent, black var(--fade-s), black calc(100% - var(--fade-e)), transparent);
	}
	/* The card's frame: a <button> for an era or tradition, a <div> holding a
	   head button and place chips for a region. */
	.band-card {
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border: 1px solid var(--border);
		border-top: 4px solid var(--hue, var(--accent));
		border-radius: var(--radius-card);
		color: var(--text);
		transition:
			background var(--duration-base, 150ms),
			border-color var(--duration-base, 150ms);
	}
	/* What the card shows: name, sub-line, faces and count. */
	.band-body {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.15rem;
		text-align: start;
		padding: 0.75rem 0.8rem 0.65rem;
		cursor: pointer;
		color: inherit;
	}
	.band-head {
		flex: 1 1 auto;
		background: none;
		border: 0;
		border-radius: var(--radius-card);
	}
	.band-card:hover {
		background: color-mix(in srgb, var(--hue, var(--accent)) 7%, var(--surface));
	}
	.band-card.on {
		background: color-mix(in srgb, var(--hue, var(--accent)) 12%, var(--surface));
		border-color: color-mix(in srgb, var(--hue, var(--accent)) 55%, var(--border));
		border-top-color: var(--hue, var(--accent));
	}
	.band-card.dim {
		opacity: 0.55;
	}
	.band-name {
		font-size: var(--fs-small);
		font-weight: 600;
		line-height: 1.25;
	}
	.band-sub {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.band-foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		margin-top: auto;
		padding-top: 0.55rem;
	}
	.band-faces {
		display: flex;
	}
	/* The faces are Portrait's elements, so these reach in with :global. These
	   rules are unlayered and so beat Portrait's Tailwind utilities (its accent
	   border, fill and text size) — the band draws its faces its own way. */
	.band-faces > :global(*) {
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 999px;
		border: 2px solid var(--surface);
		margin-inline-end: -0.45rem;
		object-fit: cover;
		filter: grayscale(1);
	}
	.band-card:hover .band-faces > :global(img),
	.band-card.on .band-faces > :global(img) {
		filter: none;
	}
	/* No hover on a touch screen, so the faces would stay grey until tapped. */
	@media (hover: none) {
		.band-faces > :global(img) {
			filter: none;
		}
	}
	.band-faces > :global(.band-initials) {
		background: color-mix(in srgb, var(--hue, var(--accent)) 22%, var(--surface));
		color: var(--text);
		font-size: var(--fs-micro);
		font-weight: 700;
		letter-spacing: -0.04em;
	}
	.band-count {
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.band-kids {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		padding: 0 0.8rem 0.7rem;
	}
	.band-kid {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		padding: 0.15rem 0.6rem;
		font-size: var(--fs-micro);
		color: var(--text);
		cursor: pointer;
		white-space: nowrap;
	}
	.band-kid:hover {
		border-color: var(--border-strong);
	}
	.band-kid.on {
		background: var(--accent-soft);
		border-color: var(--accent-soft-border);
		color: var(--accent);
		font-weight: 600;
	}
	.band-kid-n {
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	@media (pointer: coarse) {
		.band-kid {
			min-height: 2.75rem;
		}
	}
	@media (min-width: 1024px) {
		.band {
			grid-auto-flow: row;
			grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
			overflow: visible;
			-webkit-mask-image: none;
			mask-image: none;
		}
	}
</style>
