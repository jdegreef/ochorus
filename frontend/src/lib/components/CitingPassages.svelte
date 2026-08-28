<script lang="ts">
	import type { CitingPassage } from '$lib/library-public';
	import { markSnippet } from '$lib/highlight';

	// The passages that cite a reference, as the scripture pages show them.
	//
	// Deliberately NOT localized: these pages exist in English only (citations
	// are extracted by validating against English book names, so a translated
	// edition indexes essentially nothing), so the links go to the English
	// chapter rather than through localizeHref.
	let { passages }: { passages: CitingPassage[] } = $props();
</script>

<ol class="passages">
	{#each passages as p (`${p.book_slug}-${p.chapter_order}`)}
		<li class="passage">
			<a class="who" href={`/books/${p.book_slug}/${p.chapter_order}/`}>
				<span class="work">{p.book_title}</span>
				<span class="sep">·</span>
				<span class="author">{p.author_name}</span>
			</a>
			<p class="where">
				{p.chapter_title || `Chapter ${p.chapter_order}`}
				<!-- The reference AS THAT BOOK PRINTS IT. A Victorian citation reads
				     "Rom. viii. 28", and normalising it away would hide the very
				     thing that makes the excerpt verifiable against the page. -->
				<span class="cited">cites {p.ref}</span>
			</p>
			<!-- markSnippet escapes first, then turns the backend's full-text
			     markers into <mark> — the same path the search results use. -->
			<!-- eslint-disable-next-line svelte/no-at-html-tags -->
			<p class="excerpt">{@html markSnippet(p.excerpt)}</p>
		</li>
	{/each}
</ol>

<style>
	.passages {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.9rem;
	}
	.passage {
		padding: 0.9rem 1.1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.who {
		font-weight: 600;
		color: var(--color-text);
		text-decoration: none;
	}
	.who:hover .work {
		text-decoration: underline;
	}
	.sep {
		color: var(--color-muted);
		margin: 0 0.3rem;
	}
	.author {
		font-weight: 400;
		color: var(--color-muted);
	}
	.where {
		margin: 0.15rem 0 0.5rem;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.cited {
		margin-inline-start: 0.4rem;
		font-variant: small-caps;
	}
	.excerpt {
		margin: 0;
		font-size: var(--fs-small);
		line-height: 1.6;
		color: var(--color-text);
	}
	.excerpt :global(mark) {
		background: color-mix(in srgb, var(--color-accent) 22%, transparent);
		color: inherit;
		border-radius: 2px;
		padding: 0 0.1em;
	}
</style>
