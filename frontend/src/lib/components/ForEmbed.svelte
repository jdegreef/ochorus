<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import EmbedToday from '$lib/components/EmbedToday.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { SITE_URL } from '$lib/config';
	import { embedFrameSnippet, embedSnippet, embedUrl } from '$lib/embed';
	import type { ForChrome } from '$lib/forChrome';

	/**
	 * An "Ochorus for …" page's website kit: the one-line tag that puts the
	 * "Today from Ochorus" widget ($lib/embed) on a church's own site, shown in
	 * full so a web volunteer can see exactly what they paste, with one tap to
	 * copy it and a link to the widget itself; the plain-iframe version for a
	 * builder that strips scripts, folded away; and the card as their visitors
	 * will see it (EmbedToday, inline — this page's own look, not a frame).
	 * ForInvite's shape and copy behaviour; its words come with the page's copy
	 * ($lib/forChrome).
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

	type Kind = 'script' | 'frame';
	const snippets = $derived<Record<Kind, string>>({
		script: embedSnippet(SITE_URL, locale),
		frame: embedFrameSnippet(SITE_URL, locale)
	});
	const preview = $derived(embedUrl(SITE_URL, locale));
	const codes: Partial<Record<Kind, HTMLElement>> = $state({});
	/** What the last copy did, and of which code: done, or select-it-yourself. */
	let copied = $state<{ kind: Kind; how: 'yes' | 'select' } | null>(null);
	let timer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(timer));

	// The live card fetches the day's picks (the sermon list among them), so it
	// mounts only as the section nears the screen: most visits to a /for/
	// page never scroll this far.
	let previewBox = $state<HTMLElement>();
	let near = $state(false);
	$effect(() => {
		if (!previewBox || near) return;
		if (typeof IntersectionObserver === 'undefined') return void (near = true);
		const io = new IntersectionObserver((e) => e.some((x) => x.isIntersecting) && (near = true), {
			rootMargin: '400px 0px'
		});
		io.observe(previewBox);
		return () => io.disconnect();
	});

	async function copy(kind: Kind) {
		try {
			await navigator.clipboard.writeText(snippets[kind]);
			copied = { kind, how: 'yes' };
			onaction?.(kind === 'script' ? 'embed-copy' : 'embed-copy-frame');
		} catch {
			// No clipboard here: select the code so Ctrl+C copies it, and say so.
			const code = codes[kind];
			if (code) getSelection()?.selectAllChildren(code);
			copied = { kind, how: 'select' };
		}
		clearTimeout(timer);
		timer = setTimeout(() => (copied = null), 4000);
	}
</script>

{#snippet code(kind: Kind)}
	{@const done = copied?.kind === kind ? copied.how : null}
	<!-- Code reads left to right in every language. -->
	<pre class="snippet text-small" dir="ltr"><code bind:this={codes[kind]}>{snippets[kind]}</code></pre>
	<div class="mt-4 flex flex-wrap items-center gap-2">
		<button type="button" class="btn btn-sm" onclick={() => copy(kind)}>
			<Icon name={done === 'yes' ? 'check' : 'page'} size={15} />
			{done === 'yes' ? words.copied : words.copy}
		</button>
		{#if kind === 'script'}
			<a
				class="btn btn-sm"
				href={preview}
				target="_blank"
				rel="noopener"
				onclick={() => onaction?.('embed-preview')}>{words.preview} <Arrow /></a
			>
		{/if}
		<!-- The copy's outcome, announced apart from the button that caused it. -->
		<span class="text-small text-muted" role="status"
			>{#if done === 'select'}{words.selected}{:else if done === 'yes'}<span class="sr-only"
					>{words.announced}</span
				>{/if}</span
		>
	</div>
{/snippet}

<div class="rounded-card border border-border bg-surface p-5">
	{@render code('script')}
	<p class="mt-3 text-small text-muted">{words.options}</p>
	<details class="mt-4 border-t border-border pt-4">
		<summary class="text-small font-semibold">{words.frameSummary}</summary>
		<p class="mt-2 text-small text-muted">{words.frameBody}</p>
		<div class="mt-3">{@render code('frame')}</div>
	</details>
</div>

<p class="mt-6 text-eyebrow text-muted">{words.previewLabel}</p>
<div class="preview mt-2" bind:this={previewBox}>
	{#if near}<EmbedToday onopen={(part) => onaction?.(`embed-preview-${part}`)} />{/if}
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
	summary {
		cursor: pointer;
	}
	/* A sidebar's width, the shape most churches will give it; held open
	   before the card mounts so the page does not jump when it does. */
	.preview {
		max-width: 22rem;
		min-height: 20rem;
	}
</style>
