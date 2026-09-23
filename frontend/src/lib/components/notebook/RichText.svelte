<script lang="ts">
	import { parseRichText, type Line } from '$lib/richText';

	/**
	 * An entry's words with their formatting — bold, italic, lists, quotations
	 * (see $lib/richText). Built from text nodes, never {@html}, so what a reader
	 * typed can only ever be text. Inherits the surrounding type and line height,
	 * so it sits on the Notebook's ruled lines like plain text did.
	 */
	let { text }: { text: string } = $props();
	const blocks = $derived(parseRichText(text));
</script>

{#snippet spans(line: Line)}{#each line as s, i (i)}{#if s.bold && s.italic}<strong><em>{s.text}</em></strong
			>{:else if s.bold}<strong>{s.text}</strong>{:else if s.italic}<em>{s.text}</em>{:else}{s.text}{/if}{/each}{/snippet}

<div class="rich">
	{#each blocks as b, i (i)}
		{#if b.type === 'p'}
			<p>{#each b.lines as line, j (j)}{#if j}<br />{/if}{@render spans(line)}{/each}</p>
		{:else if b.type === 'ul'}
			<ul>{#each b.items as item, j (j)}<li>{@render spans(item)}</li>{/each}</ul>
		{:else if b.type === 'ol'}
			<ol start={b.start}>{#each b.items as item, j (j)}<li>{@render spans(item)}</li>{/each}</ol>
		{:else}
			<blockquote>{#each b.lines as line, j (j)}{#if j}<br />{/if}{@render spans(line)}{/each}</blockquote>
		{/if}
	{/each}
</div>

<style>
	/* One ruled line between blocks — the page's own rule gap where there is
	   one — so paragraphs stand apart and the words still sit on the rules. */
	.rich > * + * {
		margin-top: var(--rule-gap, 0.75em);
	}
	.rich strong {
		font-weight: 700;
	}
	ul,
	ol {
		padding-inline-start: 1.4rem;
	}
	ul {
		list-style: disc;
	}
	ol {
		list-style: decimal;
	}
	blockquote {
		padding-inline-start: 0.9rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--gold) 55%, transparent);
		font-style: italic;
		color: var(--muted);
	}
	blockquote em {
		font-style: normal;
	}
</style>
