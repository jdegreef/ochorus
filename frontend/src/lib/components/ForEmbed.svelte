<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { SITE_URL } from '$lib/config';
	import { embedSnippet } from '$lib/embed';
	import type { ForChrome } from '$lib/forChrome';

	/**
	 * An "Ochorus for …" page's website kit: the one-line tag that puts the
	 * "Today from Ochorus" widget ($lib/embed) on a church's own site, shown in
	 * full so a web volunteer can see exactly what they paste, with one tap to
	 * copy it and a link to the widget itself. ForInvite's shape and copy
	 * behaviour; its words come with the page's copy ($lib/forChrome).
	 */
	let {
		locale,
		words,
		onaction
	}: {
		/** The page's language, which the widget is set to. */
		locale: string;
		words: ForChrome['embed'];
		/** Reports what the leader did, for the page's analytics. */
		onaction?: (action: string) => void;
	} = $props();

	const snippet = $derived(embedSnippet(SITE_URL, locale));
	const preview = $derived(`${SITE_URL}${locale === 'en' ? '' : `/${locale}`}/embed/today`);
	let code = $state<HTMLElement>();
	/** What the last copy did, for the status line: done, or select-it-yourself. */
	let copied = $state<'yes' | 'select' | null>(null);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));

	async function copy() {
		try {
			await navigator.clipboard.writeText(snippet);
			copied = 'yes';
			onaction?.('embed-copy');
		} catch {
			// No clipboard here: select the code so Ctrl+C copies it, and say so.
			if (code) getSelection()?.selectAllChildren(code);
			copied = 'select';
		}
		clearTimeout(timer);
		timer = setTimeout(() => (copied = null), 4000);
	}
</script>

<div class="rounded-card border border-border bg-surface p-5">
	<!-- Code reads left to right in every language. -->
	<pre class="snippet text-small" dir="ltr"><code bind:this={code}>{snippet}</code></pre>
	<p class="mt-3 text-small text-muted">{words.options}</p>
	<div class="mt-4 flex flex-wrap items-center gap-2">
		<button type="button" class="btn btn-sm" onclick={copy}>
			<Icon name={copied === 'yes' ? 'check' : 'page'} size={15} />
			{copied === 'yes' ? words.copied : words.copy}
		</button>
		<a
			class="btn btn-sm"
			href={preview}
			target="_blank"
			rel="noopener"
			onclick={() => onaction?.('embed-preview')}>{words.preview} <Arrow /></a
		>
		<!-- The copy's outcome, announced apart from the button that caused it. -->
		<span class="text-small text-muted" role="status"
			>{#if copied === 'select'}{words.selected}{:else if copied === 'yes'}<span class="sr-only"
					>{words.announced}</span
				>{/if}</span
		>
	</div>
</div>

<style>
	.snippet {
		margin: 0;
		padding: 0.75rem 1rem;
		border-radius: var(--radius-card);
		background: var(--bg);
		border: 1px solid var(--border);
		font-family: var(--font-mono, ui-monospace, monospace);
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		text-align: start;
	}
</style>
