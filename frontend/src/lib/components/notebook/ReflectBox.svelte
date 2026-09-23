<script lang="ts">
	import type { Snippet } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { reflectionFor, type EntrySource } from '$lib/journal';
	import { journal } from '$lib/journal.svelte';
	import EntryComposer from './EntryComposer.svelte';
	import RichText from './RichText.svelte';

	/**
	 * A place to answer what the reading asks — a plan day's reflection, a
	 * sermon's study question — that writes into the Notebook: a note titled
	 * with the question (or the day), filed in a collection named for the plan
	 * or sermon, carrying where it was written as its source. Once written, the
	 * reader's own answer shows here instead, with the way to it in the Notebook.
	 *
	 * Loaded on demand by the reading pages (it brings the journal store with it).
	 */
	let {
		heading = '',
		prompt,
		title,
		collection,
		source,
		compact = false,
		children
	}: {
		/** Shown above the box; '' when the page already says what is asked. */
		heading?: string;
		/** The invitation in the empty box — the question, or a reflection prompt. */
		prompt: string;
		/** The saved note's title, and how this place's answer is found again. */
		title: string;
		collection: string;
		source: EntrySource;
		/** A quiet "Write your answer" until tapped — for a list of questions,
		 *  where a composer under every one would crowd the page. */
		compact?: boolean;
		/** Anything the page adds under a written answer (e.g. "mark today done"). */
		children?: Snippet;
	} = $props();

	const t = i18n.t;
	const written = $derived(reflectionFor(journal.store, source, title));
	let asked = $state(false);
	const notebookHref = $derived(
		written
			? localizeHref(`/notebook?collection=${encodeURIComponent(written.collection || collection)}#entry-${written.id}`)
			: ''
	);
</script>

<div class="reflect">
	{#if heading}<p class="heading">{heading}</p>{/if}
	{#if written}
		<div class="answer">
			<p class="label text-micro">✓ {t('notebook.reflectSaved')}</p>
			<div class="text"><RichText text={written.body} /></div>
			<a class="text-small font-semibold" href={notebookHref}>{t('notebook.reflectOpen')} →</a>
		</div>
		{#if children}<div class="mt-3">{@render children()}</div>{/if}
	{:else if compact && !asked}
		<button class="write text-small" onclick={() => (asked = true)}>
			<span aria-hidden="true" class="me-1">✎</span>{t('notebook.reflectWrite')}
		</button>
	{:else}
		<EntryComposer
			editing={compact}
			defaults={{ kind: 'note', title, collection }}
			placeholder={prompt}
			onsave={(d) => journal.add(d, source)}
			oncancel={compact ? () => (asked = false) : undefined}
		/>
	{/if}
</div>

<style>
	.write {
		color: var(--accent);
		font-weight: 600;
		cursor: pointer;
	}
	.write:hover {
		text-decoration: underline;
	}
	.heading {
		margin-bottom: 0.6rem;
		font-family: var(--font-display);
		font-style: italic;
		color: var(--text);
	}
	.answer {
		padding: 0.85rem 1rem;
		border-inline-start: 3px solid color-mix(in srgb, var(--gold) 60%, transparent);
		background: color-mix(in srgb, var(--gold) 7%, var(--surface));
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
	}
	:global([dir='rtl']) .answer {
		border-radius: var(--radius-sm) 0 0 var(--radius-sm);
	}
	.label {
		color: var(--warning);
		font-weight: 600;
	}
	.text {
		margin: 0.3rem 0 0.5rem;
		font-family: var(--font-display);
		line-height: 1.6;
		color: var(--text);
		display: -webkit-box;
		-webkit-line-clamp: 6;
		line-clamp: 6;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
