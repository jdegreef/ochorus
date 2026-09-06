<script lang="ts">
	// A themed Scripture epigraph, set off by an accent rule — the furniture the
	// topic pages carry over their heading. Renders nothing without text, so a
	// caller can pass an untranslated/absent verse unguarded.
	//
	// `hue` is any CSS colour expression (default the accent); the work-topic
	// shelves pass their topic hue, the quote-theme pages the accent. Every use
	// goes through color-mix, never as body text, so contrast holds in both
	// themes (STYLE_GUIDE §5). padding-inline-start, not padding-left, so the
	// rule stays on the reading edge under RTL (Arabic).
	let {
		text,
		reference = '',
		hue = 'var(--color-accent)'
	}: { text: string; reference?: string; hue?: string } = $props();
</script>

{#if text}
	<figure class="verse" style={`--epi-hue: ${hue}`}>
		<blockquote>{text}</blockquote>
		{#if reference}
			<figcaption>— {reference}</figcaption>
		{/if}
	</figure>
{/if}

<style>
	.verse {
		margin: 0.9rem 0 0;
		padding-inline-start: 0.9rem;
		border-inline-start: 2px solid color-mix(in srgb, var(--epi-hue) 55%, var(--color-border));
	}
	.verse blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		font-size: var(--fs-body);
		line-height: 1.5;
		color: var(--color-text);
	}
	.verse figcaption {
		margin-top: 0.3rem;
		font-size: var(--fs-small);
		letter-spacing: 0.02em;
		color: color-mix(in srgb, var(--epi-hue) 70%, var(--color-muted));
	}
</style>
