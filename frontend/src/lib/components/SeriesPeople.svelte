<script lang="ts">
	import { bookChapterPath } from '$lib/reading-schema';
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
	// One even wall when the volumes hold uneven numbers of faces (Brave for
	// God: 6, 5, 5, 1 — a lone face under the last heading): every face in one
	// grid, each card naming its volume. Grouped otherwise (They Were Young).
	const even = $derived(groups.every((g) => g.people.length === groups[0].people.length));
	const wall = $derived(groups.flatMap((g) => g.people.map((p) => ({ p, book: g.book }))));
	const heading = (b: SeriesBook) =>
		[volumeLabel(b.series_position, lang), volumeName(b, seriesTitle)].filter(Boolean).join(' · ') ||
		b.title;
</script>

{#snippet face(p: HubPerson, volume: string)}
	<a href={localizeHref(bookChapterPath(p.book, p.chapter, false))} class="face card-lift">
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
		{#if volume}<span class="face-volume eyebrow" dir="auto">{volume}</span>{/if}
		<span class="face-name" dir="auto">{p.name}</span>
		<span class="face-hook" dir="auto">{p.hook}</span>
		{#if p.words}<span class="face-time">{readingTime(p.words)}</span>{/if}
	</a>
{/snippet}

{#if !even && groups.length > 1}
	<ul class="faces wall">
		{#each wall as { p, book } (`${p.book}/${p.chapter}`)}
			<li>{@render face(p, volumeLabel(book.series_position, lang) || heading(book))}</li>
		{/each}
	</ul>
{:else}
<div class="groups">
	{#each groups as g (g.book.slug)}
		<div class="group">
			<h3 class="eyebrow group-name" dir="auto">{heading(g.book)}</h3>
			<ul class="faces">
				{#each g.people as p (`${p.book}/${p.chapter}`)}
					<li>{@render face(p, '')}</li>
				{/each}
			</ul>
		</div>
	{/each}
</div>
{/if}

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
	/* The flat wall centres its rows, so a short last row sits under the
	   middle of the wall rather than hanging off its first column. */
	.faces.wall {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
	}
	.faces.wall > li {
		flex: 0 0 8.5rem;
	}
	.face-volume {
		margin-top: 0.6rem;
		color: var(--series-accent, var(--accent));
	}
	.face-volume + .face-name {
		margin-top: 0.2rem;
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
