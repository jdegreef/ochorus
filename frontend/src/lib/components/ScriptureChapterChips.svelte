<script lang="ts">
	import { scripturePageHref } from '$lib/library-public';

	/**
	 * One Bible book's chapter pages as a wrapping row of numbered chips, each
	 * shaded by how many passages cite it (`heat`, from scriptureIndex.heatScale,
	 * 0–4; the shades are the shared `.heat-N` classes in app.css, which the
	 * hub's legend uses too). The /scripture hub draws one row per book; the
	 * /scripture/<book>/ page draws its own book's.
	 */
	let {
		book,
		chapters,
		heat,
		passages
	}: {
		book: { slug: string; title: string };
		chapters: { chapter: number; count: number }[];
		heat: (count: number) => number;
		/** "N passages", already localized. */
		passages: (count: number) => string;
	} = $props();
</script>

<ul class="chapters">
	{#each chapters as c (c.chapter)}
		<li>
			<a
				href={scripturePageHref(book.slug, c.chapter, null)}
				class="heat-{heat(c.count)}"
				title={passages(c.count)}
				aria-label="{book.title} {c.chapter}, {passages(c.count)}">{c.chapter}</a
			>
		</li>
	{/each}
</ul>

<style>
	.chapters {
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin: 0;
		padding: 0;
	}
	.chapters a {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2rem;
		padding: 0.15rem 0.45rem;
		text-align: center;
		font-variant-numeric: tabular-nums;
		font-size: var(--fs-small);
		border-radius: var(--radius-sm);
		color: var(--color-text);
		text-decoration: none;
	}
	/* On touch, each chapter number is a 44px square: 708 of them were 26px
	   tall, a grid you had to aim at. */
	@media (pointer: coarse) {
		.chapters a {
			min-width: 2.75rem;
			min-height: 2.75rem;
		}
	}
	/* The top shade is the solid accent: its ink needs this rule's specificity
	   to beat the body colour above. */
	.chapters a.heat-4 {
		color: var(--color-accent-contrast);
		font-weight: 600;
	}
	.chapters a:hover {
		outline: 2px solid var(--color-accent);
		outline-offset: 1px;
	}
</style>
