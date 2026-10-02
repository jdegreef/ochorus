<script lang="ts">
	import { onMount } from 'svelte';
	import type { Quote } from '$lib/library-public';
	import { getQuoteContext, quoteHref } from '$lib/library-public';
	import QuoteText from '$lib/components/QuoteText.svelte';
	import { splitAround } from '$lib/quoteText';
	import { i18n } from '$lib/i18n.svelte';

	// The quotation inside the paragraph it was taken from — the strongest proof
	// a card can give that the line is the author's and is not lifted out of
	// context. Mounted only when the reader opens it, so it fetches then, once.
	// Plain text from the API: the sentence is highlighted here and the reader
	// link carries on to the real, formatted page.
	let { quote }: { quote: Quote } = $props();
	const t = i18n.t;

	let text = $state<string | null>(null);
	let failed = $state(false);
	const parts = $derived(text === null ? null : splitAround(text, quote.text));

	onMount(async () => {
		try {
			text = (await getQuoteContext(quote.slug)).paragraph_text;
		} catch {
			failed = true;
		}
	});
</script>

<div class="context" aria-live="polite">
	{#if failed}
		<p class="note">{t('quotes.contextError')}</p>
	{:else if parts === null}
		<p class="note" aria-busy="true">…</p>
	{:else}
		<p class="para">
			{#if parts}<QuoteText text={parts.before} /><mark><QuoteText text={parts.match} /></mark
				><QuoteText text={parts.after} />{:else}<QuoteText text={text ?? ''} />{/if}
		</p>
	{/if}
	<a class="go" href={quoteHref(quote)}>{t('quotes.continueReading')}</a>
</div>

<style>
	.context {
		margin-top: 0.8rem;
		padding: 0.8rem 1rem;
		border-inline-start: 3px solid var(--color-border-strong);
		background: var(--color-surface-2);
		border-radius: var(--radius-sm);
	}
	.para {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		line-height: 1.6;
		color: var(--color-muted);
	}
	/* The quoted sentence stands out of its paragraph in the text colour on a
	   gold wash — the reader's own highlight hue, so it reads as "this line". */
	mark {
		color: var(--color-text);
		background: color-mix(in srgb, var(--color-gold) 22%, transparent);
		border-radius: 2px;
		padding: 0 1px;
	}
	.note {
		margin: 0;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.go {
		display: inline-block;
		margin-top: 0.5rem;
		font-size: var(--fs-small);
		color: var(--color-accent);
		text-decoration: none;
	}
	.go:hover {
		text-decoration: underline;
	}
</style>
