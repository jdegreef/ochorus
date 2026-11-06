<script lang="ts">
	import { assetUrl } from '$lib/assetUrl';
	import type { Snippet } from 'svelte';
	import { eraById, eraOf } from '$lib/eras';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { initials, portraitPosition } from '$lib/portraits';

	/**
	 * The author page's masthead, laid out as the book page's hero (design
	 * review #13): the portrait on the start side where the book page hangs its
	 * cover, the era eyebrow, the name and its one line beside it, and the key
	 * facts and the page's actions under those.
	 *
	 * Light, on the page's own ground. It used to be a dark band of the era's
	 * colour with the portrait printed as a duotone in a gilt frame — the one
	 * page with a slab hero, and a Victorian photograph that looked like a
	 * filter mistake. The portrait is now the photograph as it is (no
	 * `.duotone`, no grayscale) in a light print frame.
	 *
	 * A phone: a small portrait BESIDE the name (it used to fill the first
	 * screen before the name was reached), the facts and actions full width
	 * beneath — the book page's phone grid.
	 *
	 * No free image: the frame carries the writer's initials. The portrait is
	 * decoration (the name is the heading beside it), so its alt is empty. It
	 * is the page's LCP on a desktop, so it is fetched eagerly and high, and
	 * states the print's 4:5 as its intrinsic size.
	 */
	let {
		slug,
		name,
		photoUrl,
		birthYear,
		children,
		details
	}: {
		slug: string;
		name: string;
		photoUrl?: string | null;
		birthYear: number | null;
		/** The heading and the one-line identity, beside the portrait. */
		children: Snippet;
		/** The key facts and the actions: beside the portrait from sm, full
		 *  width under it on a phone. */
		details?: Snippet;
	} = $props();
	const t = i18n.t;

	// An unknown birth year has no era, and so no eyebrow.
	const era = $derived(birthYear == null ? null : eraById(eraOf(birthYear)));
</script>

<header class="author-hero">
	<figure class="author-hero-print">
		{#if photoUrl}
			{@const src = assetUrl(photoUrl)}
			<img
				{src}
				use:hydrateSrc={{ src }}
				alt=""
				loading="eager"
				fetchpriority="high"
				width="200"
				height="250"
				style:object-position={portraitPosition(slug)}
			/>
		{:else}
			<span class="author-hero-initials font-display" aria-hidden="true">{initials(name)}</span>
		{/if}
	</figure>
	<div class="author-hero-head min-w-0">
		{#if era}
			<p class="eyebrow mb-1 text-muted">{t(era.k)}</p>
		{/if}
		{@render children()}
	</div>
	{#if details}
		<div class="author-hero-details min-w-0">
			{@render details()}
		</div>
	{/if}
</header>

<style>
	/* On the reading column, as the read card and every section below it. */
	.author-hero {
		max-width: 40rem;
		margin-inline: auto;
		margin-top: 1.25rem;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		column-gap: 1rem;
		align-items: start;
	}
	.author-hero-details {
		grid-column: 1 / -1;
	}
	/* A light print: the photograph on a thin surface mat with a hairline
	   edge, raised a little off the page like the book page's cover. */
	.author-hero-print {
		margin: 0;
		width: 5.5rem;
		aspect-ratio: 4 / 5;
		padding: 0.25rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}
	.author-hero-print img,
	.author-hero-initials {
		display: flex;
		width: 100%;
		height: 100%;
		border-radius: calc(var(--radius-sm) - 0.25rem);
	}
	.author-hero-print img {
		object-fit: cover;
	}
	.author-hero-initials {
		align-items: center;
		justify-content: center;
		background: var(--accent-soft);
		color: var(--accent);
		font-size: var(--fs-h2);
		font-weight: 600;
	}
	@media (min-width: 640px) {
		/* A last row takes up the portrait's spare height, so the name, the
		   facts and the actions stack tight at the top beside it. */
		.author-hero {
			grid-template-rows: auto 1fr;
			column-gap: 1.75rem;
		}
		.author-hero-print {
			grid-row: 1 / -1;
			width: 11rem;
			padding: 0.35rem;
		}
		.author-hero-print img,
		.author-hero-initials {
			border-radius: calc(var(--radius-sm) - 0.35rem);
		}
		.author-hero-initials {
			font-size: var(--fs-display);
		}
		.author-hero-details {
			grid-column: 2;
		}
	}
	@media print {
		.author-hero-print {
			box-shadow: none;
		}
	}
</style>
