<script lang="ts">
	import { localizeHref } from '$lib/href';
	import { readingTime } from '$lib/reading';
	import { volumeLabel, volumeName } from '$lib/series';
	import type { HubPerson, SeriesBook } from '$lib/library-public';
	import Portrait from './Portrait.svelte';

	/**
	 * The faces of the real people a series' volumes tell — They Were Young's
	 * twenty-four lives — grouped by volume, each opening its own chapter. The
	 * hub's people strip, as a wall: the same `HubPerson`s (name and hook are
	 * the chapter's own title, in this language), the same portrait recipe.
	 */
	let {
		people,
		books,
		seriesTitle,
		lang
	}: { people: HubPerson[]; books: SeriesBook[]; seriesTitle: string; lang: string } = $props();

	// Volume order is the page's; a face whose book isn't listed is dropped.
	const groups = $derived(
		books
			.map((book) => ({ book, people: people.filter((p) => p.book === book.slug) }))
			.filter((g) => g.people.length)
	);
	const heading = (b: SeriesBook) =>
		[volumeLabel(b.series_position, lang), volumeName(b, seriesTitle)].filter(Boolean).join(' · ') ||
		b.title;
</script>

<div class="groups">
	{#each groups as g (g.book.slug)}
		<div class="group">
			<h3 class="eyebrow group-name" dir="auto">{heading(g.book)}</h3>
			<ul class="faces">
				{#each g.people as p (`${p.book}/${p.chapter}`)}
					<li>
						<a href={localizeHref(`/books/${p.book}/${p.chapter}`)} class="face card-lift">
							<Portrait
								slug={p.slug}
								name={p.name}
								url={p.photo_url}
								px={80}
								class="size-20 rounded-full object-cover"
								initialsClass="text-h3"
								tone="hover"
								decorative
							/>
							<span class="face-name" dir="auto">{p.name}</span>
							<span class="face-hook" dir="auto">{p.hook}</span>
							{#if p.words}<span class="face-time">{readingTime(p.words)}</span>{/if}
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/each}
</div>

<style>
	.groups {
		display: grid;
		gap: 1.75rem;
	}
	.group-name {
		color: var(--series-accent, var(--accent));
		margin: 0 0 0.75rem;
	}
	.faces {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr));
		gap: 0.75rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.face {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		height: 100%;
		padding: 1rem 0.75rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		text-decoration: none;
	}
	.face-name {
		margin-top: 0.75rem;
		font-family: var(--font-display);
		font-weight: 600;
		line-height: 1.25;
		color: var(--text);
	}
	.face-hook {
		margin-top: 0.25rem;
		font-size: var(--fs-small);
		line-height: 1.3;
		color: var(--muted);
	}
	.face-time {
		margin-top: auto;
		padding-top: 0.5rem;
		font-size: var(--fs-eyebrow);
		color: var(--series-accent, var(--accent));
	}
</style>
