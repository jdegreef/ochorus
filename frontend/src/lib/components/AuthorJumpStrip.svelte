<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { initials } from '$lib/strings';
	import { portraitPosition, portraitSrcset } from '$lib/portraits';

	/**
	 * Jump to a writer's section on a long shelf grouped by writer — Books "By
	 * author" and Sermons "By preacher". One scrolling row of faces, each with
	 * its count: it holds its height however many writers join (the chip wall it
	 * replaced ran to three rows), and a face is found faster than a name. In
	 * section order, so the strip reads like the page below it.
	 *
	 * Draws its own portrait rather than `<Portrait>` (page-design: the strip is
	 * one of the two deliberate exceptions — the face sits in a bordered ring
	 * that lights on hover).
	 */
	export type JumpWriter = { slug: string; name: string; photo_url: string; count: number };
	let {
		writers,
		href,
		label,
		class: cls = ''
	}: {
		writers: JumpWriter[];
		/** The in-page anchor a writer's face jumps to. */
		href: (slug: string) => string;
		/** The strip's accessible name ("Jump to preacher"). */
		label: string;
		class?: string;
	} = $props();
</script>

<nav class="cover-rail flex gap-1 pb-1 {cls}" aria-label={label}>
	{#each writers as w (w.slug)}
		<a href={href(w.slug)} class="writer-jump">
			<span class="writer-face" aria-hidden="true">
				{#if w.photo_url}
					{@const source = { src: w.photo_url, srcset: portraitSrcset(w.photo_url) }}
					<img
						src={source.src}
						srcset={source.srcset}
						use:hydrateSrc={source}
						sizes="44px"
						alt=""
						loading="lazy"
						width="44"
						height="44"
						style="object-position: {portraitPosition(w.slug)}"
					/>
				{:else}
					{initials(w.name)}
				{/if}
			</span>
			<span class="writer-name">{w.name}</span>
			<span class="count text-micro">{w.count}</span>
		</a>
	{/each}
</nav>

<style>
	/* One face in the strip (the strip itself is the shared .cover-rail):
	   portrait or initials over the name and count. */
	.writer-jump {
		flex: none;
		width: 5.5rem;
		display: grid;
		justify-items: center;
		align-content: start;
		gap: 0.2rem;
		padding: 0.4rem 0.25rem;
		border-radius: var(--radius-card);
		text-align: center;
		color: var(--text);
		text-decoration: none;
	}
	.writer-jump:hover {
		background: var(--surface-2);
	}
	.writer-jump:hover .writer-face {
		border-color: var(--accent);
	}
	.writer-jump:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}
	.writer-face {
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 9999px;
		overflow: hidden;
		display: grid;
		place-items: center;
		border: 2px solid var(--border);
		background: var(--surface-2);
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--muted);
		transition: border-color var(--duration-fast);
	}
	.writer-face img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.writer-name {
		font-size: var(--fs-small);
		line-height: 1.2;
	}
</style>
