<script lang="ts">
	import type { Snippet } from 'svelte';
	import { ERA_HUE, eraById, eraOf } from '$lib/eras';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { initials, portraitPosition } from '$lib/portraits';

	/**
	 * The author page's masthead: the writer's portrait hung as a framed print —
	 * a cream mat inside a gilt fillet, the home hero's gallery frame — on a
	 * band of their era's colour, with the name and what's here beside it.
	 *
	 * The colour is the era's (ERA_HUE), the same one the writer's card wears on
	 * every shelf sorted by era, so the page and the card agree. It is mixed into
	 * --hero-tint, the palette's night shade, so the band is dark in every theme
	 * and its ink is the hero's (authorHero.test.ts measures --hero-ink on every
	 * era over every palette's tint). The portrait is printed as a duotone in the
	 * same hue (`.duotone`, app.css), so an engraving, an icon and a photograph
	 * all hang as one set.
	 *
	 * No free image: the mat carries the writer's initials in the era hue rather
	 * than an empty frame. The frame and the hue are decoration (the name is the
	 * heading beside it), so the image's alt is empty.
	 */
	let {
		slug,
		name,
		photoUrl,
		birthYear,
		years,
		children
	}: {
		slug: string;
		name: string;
		photoUrl?: string | null;
		birthYear: number | null;
		/** "1867–1951", or empty — lettered on the mat under the portrait. */
		years: string;
		/** The heading, the one-line summary and the writer's hubs. */
		children: Snippet;
	} = $props();
	const t = i18n.t;

	// An unknown birth year has no era: no eyebrow, and the band takes the
	// accent rather than claiming the Modern Era's indigo.
	const era = $derived(birthYear == null ? null : eraById(eraOf(birthYear)));
	const hue = $derived(era ? ERA_HUE[era.id] : 'var(--accent)');
</script>

<section class="author-hero" style:--era={hue}>
	<figure class="author-hero-frame">
		{#if photoUrl}
			<span class="author-hero-print duotone">
				<img
					src={photoUrl}
					use:hydrateSrc={{ src: photoUrl }}
					alt=""
					loading="eager"
					fetchpriority="high"
					style:object-position={portraitPosition(slug)}
				/>
			</span>
		{:else}
			<span class="author-hero-print author-hero-initials font-display" aria-hidden="true">{initials(name)}</span>
		{/if}
		<figcaption class="author-hero-label font-display" aria-hidden="true">
			{name}{#if years}{` · ${years}`}{/if}
		</figcaption>
	</figure>
	<div class="author-hero-text min-w-0">
		{#if era}
			<p class="eyebrow author-hero-eyebrow">{t(era.k)}</p>
		{/if}
		{@render children()}
	</div>
</section>

<style>
	.author-hero {
		--duotone-hue: var(--era);
		position: relative;
		/* A little wider than the page's 40rem reading column, so the band
		   reads as the page's opening rather than one more block in it. */
		max-width: 52rem;
		margin-inline: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.75rem;
		padding: 2rem 1.25rem 2.25rem;
		border-radius: var(--radius-card);
		color: var(--hero-ink);
		background:
			radial-gradient(
				circle at 22% 40%,
				color-mix(in srgb, var(--era) 28%, var(--hero-tint)) 0%,
				var(--hero-tint) 72%
			);
		text-align: center;
	}
	@media (min-width: 640px) {
		.author-hero {
			flex-direction: row;
			gap: 2.75rem;
			padding: 2.5rem 2.75rem;
			text-align: start;
		}
	}
	/* The gallery frame: cream mat, gilt fillet with its darker inner edge,
	   tipped a degree and a half as if hung by hand. */
	.author-hero-frame {
		flex: none;
		margin: 0;
		padding: 0.7rem 0.7rem 0.55rem;
		background: var(--hero-mat);
		border: 5px solid var(--hero-gilt);
		box-shadow:
			inset 0 0 0 2px var(--hero-gilt-deep),
			var(--hero-plate-shadow);
		/* tilt-ok: a framed portrait hung on the wall, not a book cover */
		transform: rotate(-1.5deg);
	}
	.author-hero-print {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 9.5rem;
		aspect-ratio: 4 / 5;
		overflow: hidden;
	}
	@media (min-width: 640px) {
		.author-hero-print {
			width: 12.5rem;
		}
	}
	.author-hero-print img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	/* At full strength a framed print reads as a filter; half the era's colour
	   reads as an old tinted plate. */
	.author-hero-print.duotone::after {
		opacity: 0.5;
	}
	.author-hero-initials {
		background: color-mix(in srgb, var(--era) 16%, var(--hero-mat));
		color: var(--hero-mat-ink);
		font-size: var(--fs-display);
		font-weight: 600;
	}
	.author-hero-label {
		max-width: 12.5rem;
		margin-top: 0.45rem;
		font-size: var(--fs-micro);
		font-style: italic;
		line-height: 1.3;
		text-align: center;
		color: var(--hero-mat-ink);
	}
	.author-hero-eyebrow {
		margin-bottom: 0.6rem;
		color: var(--hero-ink);
		opacity: 0.85;
	}
	/* The heading, summary and hub tags arrive from the page; on the band they
	   take the hero ink (the heading's own rule would set --text, dark in the
	   light themes). */
	.author-hero-text :global(h1) {
		color: var(--hero-ink);
	}
	.author-hero-text :global(.text-muted) {
		color: var(--hero-ink);
		opacity: 0.85;
	}
	.author-hero-text :global(.tag) {
		color: var(--hero-ink);
		border-color: var(--hero-rule);
		background: transparent;
	}
	@media print {
		.author-hero {
			color: var(--text);
			background: none;
			border: 1px solid var(--border);
		}
		.author-hero-frame {
			transform: none;
			box-shadow: none;
		}
		.author-hero-eyebrow,
		.author-hero-text :global(h1),
		.author-hero-text :global(.text-muted),
		.author-hero-text :global(.tag) {
			color: var(--text);
		}
	}
</style>
